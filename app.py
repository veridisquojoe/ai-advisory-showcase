"""
app.py
------
AI Advisory Showcase — Task Classifier & ROI Estimator
Built on the PMI/CPMAI AI task taxonomy by Joseph Eldredge

Run with:
    streamlit run app.py
"""

import re
import base64
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.classifier import classify_role
from src.exec_brief import generate_exec_brief, AVAILABLE_MODELS
from src.benchmarker import generate_benchmark, score_to_tier, DIMENSIONS
from src.presets import PRESETS
from src.govai_lookup import (
    get_industry_occupation_map,
    get_scatter_data,
    lookup_occupation,
    lookup_by_title,
    data_available,
    INDUSTRY_RATE_DEFAULTS,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WorkAI Compass",
    page_icon="🧭",
    layout="wide",
)

# ── Tab icon SVGs (Iconoir-style, 24×24 stroke paths) ─────────────────────────
def _icon_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

_TAB_SVGS = [
    # 1 — Analyze a Role: magnifying glass + crosshair (analyze / discover)
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 20 20"/><path d="M10.5 7.5v6M7.5 10.5h6"/></svg>',
    # 2 — Executive AI Brief: folded document (brief / report)
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 12h5M8 16h4"/></svg>',
    # 3 — AI Adoption Benchmark: bar chart (compare / benchmark)
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M5 21v-7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7"/><path d="M11 21V9a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12"/><path d="M17 21V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v16"/></svg>',
    # 4 — Explore All Occupations: globe with meridians
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8"/><path d="M11.5 3C9 6 7.5 9 7.5 12s1.5 6 4 9"/><path d="M12.5 3C15 6 16.5 9 16.5 12s-1.5 6-4 9"/></svg>',
    # 5 — About: open book
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M12 7C10 4.5 7.5 3.5 4 4v14c3.5-.5 6 .5 8 3"/><path d="M12 7c2-2.5 4.5-3.5 8-3v14c-3.5-.5-6 .5-8 3"/></svg>',
]

_TAB_ICON_CSS = "\n".join(
    f""".stTabs [data-baseweb="tab-list"] button:nth-of-type({i + 1})::before {{
        content: '';
        display: inline-block;
        width: 15px;
        height: 15px;
        margin-right: 6px;
        vertical-align: -3px;
        flex-shrink: 0;
        background-color: currentColor;
        -webkit-mask-image: url("{_icon_uri(svg)}");
        mask-image: url("{_icon_uri(svg)}");
        -webkit-mask-size: contain;
        mask-size: contain;
        -webkit-mask-repeat: no-repeat;
        mask-repeat: no-repeat;
    }}"""
    for i, svg in enumerate(_TAB_SVGS)
)

# ── Custom theme (Curricula-inspired: warm parchment, editorial) ──────────────
st.markdown(
    """
    <style>
    /* ── Fonts & icon library ───────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');
    @import url('https://cdn.jsdelivr.net/gh/iconoir-icons/iconoir@main/css/iconoir.css');

    /* ── Tab icons (SVG mask, one per tab) ──────────────────────────────── */
    __TAB_ICON_CSS__

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── App background ─────────────────────────────────────────────────── */
    .stApp { background-color: #F2F5FA; }
    .stApp > header { background-color: #F2F5FA; border-bottom: 1px solid #CDD4E8; }

    /* ── Main content padding ───────────────────────────────────────────── */
    .block-container {
        padding-top: 1.75rem;
        padding-bottom: 3rem;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 100% !important;
    }

    /* ── Sidebar ────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {
        background-color: #E5EBF5 !important;
        border-right: 1px solid #CDD4E8;
    }
    [data-testid="stSidebar"] h3 {
        font-family: 'Libre Baskerville', Georgia, serif;
        font-size: 1rem;
        color: #2D2926;
        letter-spacing: -0.01em;
    }

    /* ── Typography ─────────────────────────────────────────────────────── */
    h1 {
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #2D2926 !important;
        letter-spacing: -0.02em;
    }
    h2 {
        font-family: 'Libre Baskerville', Georgia, serif !important;
        color: #2D2926 !important;
        letter-spacing: -0.015em;
    }
    h3, h4 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #2D2926 !important;
        letter-spacing: -0.01em;
    }
    p, li { color: #3D3530; line-height: 1.7; }

    /* ── Tabs ───────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid #CDD4E8;
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: #6B6259 !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 6px 6px 0 0;
        border: 1px solid transparent !important;
        border-bottom: none !important;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E5EBF5 !important;
        color: #2D2926 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #F2F5FA !important;
        color: #2D2926 !important;
        font-weight: 600 !important;
        border-color: #CDD4E8 !important;
        border-bottom-color: #F2F5FA !important;
        box-shadow: 0 -2px 0 #4A5580 inset;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1.25rem;
    }

    /* ── Metrics ────────────────────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background-color: #EBF0F8;
        border: 1px solid #CDD4E8;
        border-radius: 10px;
        padding: 1rem 1.2rem;
    }
    [data-testid="metric-container"] label {
        color: #8C7F74 !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #2D2926 !important;
        font-weight: 700 !important;
    }

    /* ── Buttons ────────────────────────────────────────────────────────── */
    .stButton > button {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        border-radius: 7px;
        transition: all 0.15s ease;
        letter-spacing: -0.01em;
    }
    .stButton > button[kind="primary"] {
        background-color: #4A5580 !important;
        border-color: #4A5580 !important;
        color: #F2F5FA !important;
    }
    .stButton > button[kind="primary"]:hover:not(:disabled) {
        background-color: #3D4870 !important;
        border-color: #3D4870 !important;
        transform: translateY(-1px);
        box-shadow: 0 3px 10px rgba(74,85,128,0.25);
    }
    .stButton > button[kind="primary"]:disabled {
        background-color: #B0B8CE !important;
        border-color: #B0B8CE !important;
        color: #F2F5FA !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        border-color: #CDD4E8 !important;
        color: #2D2926 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #E5EBF5 !important;
        border-color: #B0B8CE !important;
    }

    /* ── Inputs ─────────────────────────────────────────────────────────── */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] {
        background-color: #EBF0F8 !important;
        border-color: #C8D2E5 !important;
        border-radius: 7px !important;
    }
    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="input"] > div:focus-within {
        border-color: #4A5580 !important;
        box-shadow: 0 0 0 2px rgba(74,85,128,0.15) !important;
    }
    textarea {
        background-color: #EBF0F8 !important;
        border-radius: 7px !important;
    }
    .stNumberInput input {
        background-color: #EBF0F8 !important;
    }
    /* Select slider */
    [data-testid="stSlider"] .rc-slider-track { background-color: #4A5580; }
    [data-testid="stSlider"] .rc-slider-handle {
        border-color: #4A5580;
        background-color: #F2F5FA;
    }

    /* ── Expanders ──────────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background-color: #EBF0F8 !important;
        border: 1px solid #CDD4E8 !important;
        border-radius: 8px !important;
        font-weight: 500;
        color: #2D2926 !important;
    }
    .streamlit-expanderHeader:hover {
        background-color: #DCE4F2 !important;
    }
    .streamlit-expanderContent {
        border: 1px solid #CDD4E8 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        background-color: #F7FAFE !important;
    }

    /* ── Alert / info / success / warning boxes ──────────────────────────── */
    [data-testid="stNotificationContentInfo"] {
        background-color: #EEF0F8 !important;
        border-left-color: #4A5580 !important;
        border-radius: 8px;
    }
    [data-testid="stNotificationContentSuccess"] {
        background-color: #EDF3ED !important;
        border-left-color: #5C7A5C !important;
        border-radius: 8px;
    }
    [data-testid="stNotificationContentWarning"] {
        background-color: #FBF3E8 !important;
        border-left-color: #C4956A !important;
        border-radius: 8px;
    }
    [data-testid="stNotificationContentError"] {
        background-color: #F9EDED !important;
        border-left-color: #B05C5C !important;
        border-radius: 8px;
    }
    /* Streamlit 1.35+ alert wrappers */
    .stAlert > div {
        border-radius: 8px;
    }

    /* ── Dataframe ──────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border: 1px solid #CDD4E8;
        border-radius: 8px;
        overflow: hidden;
    }

    /* ── Divider ────────────────────────────────────────────────────────── */
    hr {
        border-color: #CDD4E8 !important;
        margin: 1.5rem 0 !important;
    }

    /* ── Caption / small text ───────────────────────────────────────────── */
    .stCaption, .stCaption p {
        color: #8B96B2 !important;
        font-size: 0.8rem !important;
        line-height: 1.6;
    }

    /* ── Radio buttons ──────────────────────────────────────────────────── */
    [data-testid="stRadio"] label {
        color: #3D3530;
        font-size: 0.9rem;
    }

    /* ── App title & caption (header area) ──────────────────────────────── */
    [data-testid="stAppViewContainer"] > .main .block-container > div:first-child h1 {
        margin-bottom: 0.25rem;
    }

    /* ── Scrollbar ──────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #E5EBF5; }
    ::-webkit-scrollbar-thumb { background: #B0B8CE; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #8B96B2; }
    </style>
    """.replace("__TAB_ICON_CSS__", _TAB_ICON_CSS),
    unsafe_allow_html=True,
)

# ── Category styling ──────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "LLM": "#4f8ef7",
    "Traditional ML": "#f7a24f",
    "Automation": "#4fc98e",
    "Human Only": "#b0b0b0",
}

PRIORITY_ORDER = {"Quick Win": 0, "Medium Term": 1, "Long Term": 2}
COMPLEXITY_ORDER = {"Low": 0, "Medium": 1, "High": 2}


def color_category(val):
    color = CATEGORY_COLORS.get(val, "#eeeeee")
    return f"background-color: {color}22; color: {color}; font-weight: 600;"


# ── Inline SVG helpers (no CDN dependency) ────────────────────────────────────

# Compass for the page header (32 px, ink-blue)
_COMPASS_SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" '
    'fill="none" stroke="#4A5580" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round" style="flex-shrink:0;vertical-align:middle;">'
    '<circle cx="12" cy="12" r="9"/>'
    '<path d="M16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88z"/>'
    '</svg>'
)

# Category icons for the sidebar (16 px, each in its category color)
_SIDEBAR_CAT_ICONS = {
    "LLM": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" '
        'fill="none" stroke="#4f8ef7" stroke-width="1.75" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:5px;">'
        '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>'
        '<path d="M7 11h4M7 15h8"/>'
        '</svg>'
    ),
    "Traditional ML": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" '
        'fill="none" stroke="#f7a24f" stroke-width="1.75" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:5px;">'
        '<circle cx="4" cy="12" r="2"/><circle cx="12" cy="4" r="2"/>'
        '<circle cx="20" cy="12" r="2"/><circle cx="12" cy="20" r="2"/>'
        '<path d="M6 12h4M14 12h4M12 6v4M12 14v4"/>'
        '</svg>'
    ),
    "Automation": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" '
        'fill="none" stroke="#4fc98e" stroke-width="1.75" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:5px;">'
        '<path d="M21 12a9 9 0 1 1-3.5-7.15"/>'
        '<path d="M21 3v9h-9"/>'
        '</svg>'
    ),
    "Human Only": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" '
        'fill="none" stroke="#a0a0a0" stroke-width="1.75" stroke-linecap="round" '
        'stroke-linejoin="round" style="vertical-align:-2px;margin-right:5px;">'
        '<circle cx="12" cy="8" r="4"/>'
        '<path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>'
        '</svg>'
    ),
}


def _usage_pill(used: int, total: int, label: str = "analyses") -> str:
    """Styled HTML usage-remaining indicator to replace the emoji-dot caption."""
    remaining = total - used
    color = "#4fc98e" if remaining > 2 else ("#f7a24f" if remaining > 0 else "#e74c3c")

    def _dot_bg(i: int) -> str:
        return color if i < remaining else "#C8D2E5"

    dots = "".join(
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'margin-right:3px;background:{_dot_bg(i)};"></span>'
        for i in range(total)
    )
    return (
        f'<div style="display:inline-flex;align-items:center;gap:8px;'
        f'padding:5px 12px;background:#E5EBF5;border:1px solid #CDD4E8;'
        f'border-radius:20px;font-size:12px;color:#6B6259;margin:6px 0;">'
        f'<span style="display:flex;align-items:center;">{dots}</span>'
        f'<span><strong style="color:{color}">{remaining}</strong> of {total} {label} remaining</span>'
        f'</div>'
    )


def _render_task_table(df: pd.DataFrame) -> str:
    """Custom HTML task table — replaces st.dataframe for the role analysis results."""
    PRIORITY_CHIP = {
        "Quick Win":   ("#2a7a4f", "#d6f3e6"),
        "Medium Term": ("#8a5c00", "#fdeec9"),
        "Long Term":   ("#1a3f8a", "#dce7f9"),
    }
    CAT_CHIP = {
        "LLM":           ("#2650a8", "#dce7fa"),
        "Traditional ML":("#8a5800", "#fdecc6"),
        "Automation":    ("#1a6b42", "#d4f0e3"),
        "Human Only":    ("#5a5a5a", "#ebebeb"),
    }

    header_style = (
        "padding:9px 12px;text-align:left;font-size:10.5px;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.06em;color:#8C7F74;"
        "background:#E5EBF5;border-bottom:2px solid #CDD4E8;white-space:nowrap;"
    )
    headers = ["Task", "AI Method", "Why this method", "Tools", "Time", "Value", "Priority"]

    rows_html = ""
    for _, row in df.iterrows():
        cat = row.get("category", "")
        priority = row.get("priority", "")
        cat_fg, cat_bg = CAT_CHIP.get(cat, ("#555", "#eee"))
        p_fg, p_bg     = PRIORITY_CHIP.get(priority, ("#555", "#eee"))

        cat_chip = (
            f'<span style="background:{cat_bg};color:{cat_fg};padding:2px 9px;'
            f'border-radius:10px;font-size:11px;font-weight:700;white-space:nowrap;">{cat}</span>'
        )
        p_chip = (
            f'<span style="background:{p_bg};color:{p_fg};padding:2px 9px;'
            f'border-radius:10px;font-size:11px;font-weight:700;white-space:nowrap;">{priority}</span>'
        )
        cell = "padding:10px 12px;border-bottom:1px solid #DCE4F2;vertical-align:top;"
        rows_html += (
            f'<tr class="wai-tr">'
            f'<td style="{cell}font-weight:600;color:#2D2926;">{row.get("task","")}</td>'
            f'<td style="{cell}">{cat_chip}</td>'
            f'<td style="{cell}font-size:12px;color:#5A5048;max-width:260px;">{row.get("rationale","")}</td>'
            f'<td style="{cell}font-size:12px;color:#5A5048;">{row.get("tools_str","")}</td>'
            f'<td style="{cell}font-size:12px;white-space:nowrap;">{row.get("time_impact","")}</td>'
            f'<td style="{cell}font-size:12px;font-weight:700;color:#2D2926;white-space:nowrap;">'
            f'{row.get("annual_savings_fmt","")}</td>'
            f'<td style="{cell}">{p_chip}</td>'
            f'</tr>'
        )

    head_html = "".join(
        f'<th style="{header_style}">{h}</th>' for h in headers
    )

    return (
        '<style>.wai-tr:hover td{background:#DCE4F2!important;}</style>'
        '<div style="overflow-x:auto;border:1px solid #CDD4E8;border-radius:8px;background:#F7FAFE;">'
        '<table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;">'
        f'<thead><tr>{head_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div>'
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="padding-bottom:2px;">'
    f'<h1 style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
    f'{_COMPASS_SVG_HEADER}WorkAI Compass</h1>'
    f'<p style="margin:0 0 0.5rem;font-size:1rem;color:#8C7F74;font-style:italic;line-height:1.5;">'
    f'Data-driven AI intelligence for your role, your company, and your industry — '
    f'grounded in peer-reviewed research and government labor data.'
    f'</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Sidebar: methodology ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### About WorkAI Compass")
    st.markdown(
        "**WorkAI Compass** applies the **PMI CPMAI task classification framework** "
        "to break down any role into its component tasks and assess which "
        "delivery method fits each one."
    )
    st.markdown("**Four categories:**")
    _cat_descriptions = {
        "LLM":            "language generation, summarization, Q&amp;A, drafting",
        "Traditional ML": "prediction, classification, anomaly detection",
        "Automation":     "rule-based, deterministic, scripted workflows",
        "Human Only":     "relationship, negotiation, ethical judgment",
    }
    _cats_html = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:6px;margin-bottom:8px;">'
        f'{_SIDEBAR_CAT_ICONS[cat]}'
        f'<span style="font-size:13px;line-height:1.5;">'
        f'<strong>{cat}</strong> — {desc}'
        f'</span></div>'
        for cat, desc in _cat_descriptions.items()
    )
    st.markdown(_cats_html, unsafe_allow_html=True)
    st.divider()
    st.markdown(
        "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com) · "
        "PMP, CPMAI · AI impact advisory for all kinds of organizations."
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_analyze, tab_exec, tab_benchmark, tab_explore, tab_about = st.tabs([
    "Analyze a Role",
    "Executive AI Brief",
    "AI Adoption Benchmark",
    "Explore All Occupations",
    "About",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXECUTIVE AI BRIEF
# ════════════════════════════════════════════════════════════════════════════════
with tab_exec:

    # ── Privacy disclaimer ────────────────────────────────────────────────────
    st.info(
        "🔒 **Privacy & data notice** — This analysis is generated by "
        "[Claude](https://www.anthropic.com/claude) (Anthropic). Your inputs are sent to "
        "Anthropic's API and processed under their standard "
        "[privacy policy](https://www.anthropic.com/privacy). "
        "This application does not store, log, or share your inputs beyond that API call. "
        "Avoid entering personally identifiable or confidential business information.",
        icon=None,
    )

    COMPANY_TYPES = [
        "— select a company type —",
        "B2B SaaS / Software",
        "Professional Services (consulting, legal, accounting)",
        "Healthcare System / Provider",
        "Financial Services / Banking",
        "Manufacturing / Industrial",
        "Retail / Consumer Goods",
        "Nonprofit / Social Services",
        "Government / Public Sector",
        "Education / Training",
        "Real Estate",
        "Media / Publishing / Content",
        "Logistics / Supply Chain",
        "Other",
    ]

    COMPANY_SIZES = [
        "— select a size —",
        "Small (1–49 employees)",
        "Mid-market (50–499 employees)",
        "Large (500–4,999 employees)",
        "Enterprise (5,000+ employees)",
    ]

    PRIORITY_COLORS_EXEC = {
        "Quick Win": "#4fc98e",
        "Medium Term": "#f7a24f",
        "Long Term": "#4f8ef7",
    }

    INVEST_COLORS = {
        "Low (<$10K)": "#4fc98e",
        "Medium ($10K–$100K)": "#f7a24f",
        "High (>$100K)": "#e74c3c",
    }

    st.markdown("#### Configure your company profile")
    ec1, ec2, ec3, ec4 = st.columns([1.2, 1.2, 1.2, 1])

    with ec1:
        # Reuse GovAI industry groups so language is consistent across tabs
        if industry_map := get_industry_occupation_map():
            exec_industry_options = ["— select an industry —"] + sorted(industry_map.keys())
        else:
            exec_industry_options = ["— select an industry —"] + [
                "Technology & IT", "Finance, Insurance & Real Estate",
                "Healthcare & Medical", "Government & Public Safety",
                "Education & Library", "Manufacturing & Production",
                "Legal", "Arts, Design & Media", "Other",
            ]
        exec_industry = st.selectbox(
            "Industry", exec_industry_options, key="exec_industry"
        )

    with ec2:
        exec_company_type = st.selectbox(
            "Company type", COMPANY_TYPES, key="exec_company_type"
        )

    with ec3:
        exec_company_size = st.selectbox(
            "Company size", COMPANY_SIZES, key="exec_company_size"
        )

    with ec4:
        exec_model_label = st.selectbox(
            "Claude model",
            list(AVAILABLE_MODELS.keys()),
            key="exec_model",
            help="Opus produces more thorough analysis but takes ~2× longer and costs more.",
        )
        exec_model = AVAILABLE_MODELS[exec_model_label]

    exec_context = st.text_area(
        "Additional context (optional)",
        height=90,
        placeholder=(
            "e.g. key workflows you want addressed, current tech stack, "
            "pain points, strategic priorities, budget range..."
        ),
        key="exec_context",
    )

    # ── Usage limit ───────────────────────────────────────────────────────────
    MAX_EXEC = 5
    if "exec_analyses_used" not in st.session_state:
        st.session_state["exec_analyses_used"] = 0

    exec_used = st.session_state["exec_analyses_used"]
    exec_remaining = MAX_EXEC - exec_used

    exec_inputs_ready = (
        exec_industry != "— select an industry —"
        and exec_company_type != "— select a company type —"
        and exec_company_size != "— select a size —"
    )

    if exec_remaining > 0:
        st.markdown(_usage_pill(exec_used, MAX_EXEC, "briefs"), unsafe_allow_html=True)
    else:
        st.warning(
            "You've used all 5 free executive briefs for this session. "
            "Interested in unlimited access or a custom build for your organization? "
            "[Get in touch.](mailto:eldredgemc2@gmail.com)",
            icon="💡",
        )

    exec_analyze = st.button(
        "Generate AI investment brief →",
        type="primary",
        disabled=not exec_inputs_ready or exec_remaining <= 0,
        key="exec_analyze_btn",
    )

    # ── Run analysis ──────────────────────────────────────────────────────────
    if exec_analyze and exec_inputs_ready:
        with st.spinner("Building your AI investment brief..."):
            try:
                exec_result = generate_exec_brief(
                    industry=exec_industry,
                    company_type=exec_company_type,
                    company_size=exec_company_size,
                    context=exec_context.strip(),
                    model=exec_model,
                )
                st.session_state["exec_result"] = exec_result
                st.session_state["exec_analyses_used"] = exec_used + 1
            except Exception as e:
                st.error(f"Brief generation failed: {e}")
                st.stop()

    # ── Render results ────────────────────────────────────────────────────────
    if "exec_result" in st.session_state:
        er = st.session_state["exec_result"]

        st.divider()
        st.markdown(f"### {er.get('headline', 'AI Investment Brief')}")
        st.markdown(f"*{er.get('summary', '')}*")

        st.divider()
        st.markdown("#### Investment opportunity matrix")

        areas = er.get("investment_areas", [])
        for area in areas:
            priority = area.get("priority", "Medium Term")
            invest = area.get("investment_level", "Medium ($10K–$100K)")
            p_color = PRIORITY_COLORS_EXEC.get(priority, "#aaa")
            i_color = INVEST_COLORS.get(invest, "#aaa")

            with st.expander(
                f"**{area.get('area', '')}** — "
                f":{priority.replace(' ', '').lower()}[{priority}]",
                expanded=(priority == "Quick Win"),
            ):
                ia1, ia2 = st.columns([3, 1])
                with ia1:
                    st.markdown(f"**Opportunity:** {area.get('opportunity', '')}")
                    st.markdown(f"**Why now:** {area.get('rationale', '')}")
                    tools = area.get("tools", [])
                    if tools:
                        st.markdown(f"**Tools to evaluate:** {', '.join(tools)}")
                with ia2:
                    st.markdown(
                        f"<div style='padding:8px; border-left:3px solid {p_color}; "
                        f"background:{p_color}18; border-radius:4px; margin-bottom:8px'>"
                        f"<div style='font-size:11px; color:#888'>Priority</div>"
                        f"<div style='font-weight:700; color:{p_color}'>{priority}</div>"
                        f"<div style='font-size:11px; color:#aaa; margin-top:2px'>"
                        f"{area.get('time_horizon', '')}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='padding:8px; border-left:3px solid {i_color}; "
                        f"background:{i_color}18; border-radius:4px'>"
                        f"<div style='font-size:11px; color:#888'>Investment level</div>"
                        f"<div style='font-weight:700; color:{i_color}; font-size:13px'>"
                        f"{invest}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f"<div style='margin-top:8px; padding:8px; background:rgba(79,201,142,0.08); "
                    f"border-radius:4px; font-size:13px'>"
                    f"📈 <strong>Expected impact:</strong> {area.get('est_impact', '')}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.divider()
        rc1, rc2 = st.columns([1, 1])

        with rc1:
            st.markdown("#### ⚠️ Key risks to manage")
            for risk in er.get("key_risks", []):
                st.markdown(f"- {risk}")

        with rc2:
            st.markdown("#### 🚫 Common mistake")
            st.markdown(er.get("common_mistake", ""))

        st.divider()
        st.success(
            f"**Recommended first step (next 30 days):** "
            f"{er.get('recommended_first_step', '')}",
            icon="▶️",
        )

        st.divider()
        st.caption(
            "Analysis generated by Claude (Anthropic) · "
            "Industry context: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705) / GovAI · "
            "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com), PMP · CPMAI"
        )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ADOPTION BENCHMARK
# ════════════════════════════════════════════════════════════════════════════════
with tab_benchmark:

    st.info(
        "🔒 **Privacy & data notice** — Responses are sent to Anthropic's Claude API "
        "and processed under their standard [privacy policy](https://www.anthropic.com/privacy). "
        "This application does not store your inputs. Avoid entering confidential business information.",
        icon=None,
    )

    st.markdown(
        "Rate your organization across five dimensions of AI maturity. "
        "Claude benchmarks your self-assessment against sector data from McKinsey, BCG, Gartner, "
        "and IBM IBV surveys, then identifies your strongest gaps and priority actions."
    )

    # ── Company profile ───────────────────────────────────────────────────────
    st.markdown("#### Company profile")
    bm1, bm2, bm3 = st.columns(3)

    with bm1:
        bm_industry_options = (
            ["— select an industry —"] + sorted(get_industry_occupation_map().keys())
            if get_industry_occupation_map()
            else ["— select an industry —", "Technology & IT",
                  "Finance, Insurance & Real Estate", "Healthcare & Medical",
                  "Government & Public Safety", "Education & Library", "Other"]
        )
        bm_industry = st.selectbox("Industry", bm_industry_options, key="bm_industry")

    with bm2:
        BM_COMPANY_TYPES = [
            "— select a company type —",
            "B2B SaaS / Software",
            "Professional Services (consulting, legal, accounting)",
            "Healthcare System / Provider",
            "Financial Services / Banking",
            "Manufacturing / Industrial",
            "Retail / Consumer Goods",
            "Nonprofit / Social Services",
            "Government / Public Sector",
            "Education / Training",
            "Real Estate",
            "Media / Publishing / Content",
            "Logistics / Supply Chain",
            "Other",
        ]
        bm_company_type = st.selectbox("Company type", BM_COMPANY_TYPES, key="bm_company_type")

    with bm3:
        BM_SIZES = [
            "— select a size —",
            "Small (1–49 employees)",
            "Mid-market (50–499 employees)",
            "Large (500–4,999 employees)",
            "Enterprise (5,000+ employees)",
        ]
        bm_company_size = st.selectbox("Company size", BM_SIZES, key="bm_company_size")

    # ── Self-assessment ───────────────────────────────────────────────────────
    st.markdown("#### Self-assessment")
    st.caption(
        "Rate your organization on each dimension. "
        "Be honest — the benchmark is only useful if it reflects reality."
    )

    SCORE_OPTIONS = ["1 — Early", "2 — Developing", "3 — Advanced", "4 — Native"]

    dim_scores: dict[str, int] = {}
    for dim_key, (dim_label, dim_levels) in DIMENSIONS.items():
        options_with_desc = [f"{i+1} — {lvl}" for i, lvl in enumerate(dim_levels)]
        sel = st.select_slider(
            dim_label,
            options=options_with_desc,
            value=options_with_desc[0],
            key=f"bm_{dim_key}",
        )
        dim_scores[dim_key] = int(sel[0])  # first char is the number

    bm_context = st.text_area(
        "Additional context (optional)",
        height=80,
        placeholder="e.g. We recently deployed a generative AI pilot for customer service. "
                    "Our data is mostly in legacy on-prem systems.",
        key="bm_context",
    )

    # ── Live score preview ────────────────────────────────────────────────────
    bm_total = sum(dim_scores.values())
    bm_tier = score_to_tier(bm_total)
    TIER_COLORS = {
        "Low Adoption": "#e74c3c",
        "Medium Adoption": "#f7a24f",
        "High Adoption": "#4f8ef7",
        "AI Native": "#4fc98e",
    }
    tier_color = TIER_COLORS.get(bm_tier, "#aaa")
    st.markdown(
        f"<div style='margin:8px 0; padding:10px 16px; border-left:4px solid {tier_color}; "
        f"background:{tier_color}18; border-radius:4px; display:inline-block;'>"
        f"<span style='font-size:13px; color:#888'>Current self-assessment score: </span>"
        f"<strong style='font-size:18px; color:{tier_color}'>{bm_total}/20 — {bm_tier}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Usage limit ───────────────────────────────────────────────────────────
    MAX_BM = 5
    if "bm_analyses_used" not in st.session_state:
        st.session_state["bm_analyses_used"] = 0

    bm_used = st.session_state["bm_analyses_used"]
    bm_remaining = MAX_BM - bm_used

    bm_inputs_ready = (
        bm_industry != "— select an industry —"
        and bm_company_type != "— select a company type —"
        and bm_company_size != "— select a size —"
    )

    if bm_remaining > 0:
        st.markdown(_usage_pill(bm_used, MAX_BM, "benchmarks"), unsafe_allow_html=True)
    else:
        st.warning(
            "You've used all 5 free benchmarks for this session. "
            "Interested in unlimited access or a custom build? "
            "[Get in touch.](mailto:eldredgemc2@gmail.com)",
            icon="💡",
        )

    bm_analyze = st.button(
        "Generate benchmark report →",
        type="primary",
        disabled=not bm_inputs_ready or bm_remaining <= 0,
        key="bm_analyze_btn",
    )

    # ── Run analysis ──────────────────────────────────────────────────────────
    if bm_analyze and bm_inputs_ready:
        with st.spinner("Benchmarking against sector data..."):
            try:
                bm_result = generate_benchmark(
                    industry=bm_industry,
                    company_type=bm_company_type,
                    company_size=bm_company_size,
                    scores=dim_scores,
                    context=bm_context.strip(),
                )
                st.session_state["bm_result"] = bm_result
                st.session_state["bm_analyses_used"] = bm_used + 1
            except Exception as e:
                st.error(f"Benchmark generation failed: {e}")
                st.stop()

    # ── Render results ────────────────────────────────────────────────────────
    if "bm_result" in st.session_state:
        br = st.session_state["bm_result"]
        tier_c = TIER_COLORS.get(br.get("tier", ""), "#aaa")

        st.divider()

        # Tier header
        st.markdown(
            f"<h3 style='color:{tier_c}'>▐ {br.get('tier', '')} &nbsp;"
            f"<span style='font-size:16px; color:#888; font-weight:400'>"
            f"({br.get('total_score', 0)}/20)</span></h3>",
            unsafe_allow_html=True,
        )
        st.markdown(br.get("tier_description", ""))

        # ── Radar chart ───────────────────────────────────────────────────────
        dim_labels = [DIMENSIONS[k][0] for k in DIMENSIONS]
        user_vals = [br["scores"][k] for k in DIMENSIONS]
        # Parse benchmark scores from dimension_assessments text
        bench_vals = []
        for k in DIMENSIONS:
            da = br.get("dimension_assessments", {}).get(k, {})
            bench_text = da.get("benchmark", "")
            nums = re.findall(r'\b([1-4](?:\.\d)?)\b', bench_text)
            bench_vals.append(float(nums[0]) if nums else 2.0)

        # Convert hex tier color to rgba for fill
        def _hex_to_rgba(hex_color: str, alpha: float) -> str:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=bench_vals + [bench_vals[0]],
            theta=dim_labels + [dim_labels[0]],
            fill="toself",
            name="Sector benchmark",
            line=dict(color="rgba(150,150,150,0.7)"),
            fillcolor="rgba(150,150,150,0.15)",
        ))
        radar_fig.add_trace(go.Scatterpolar(
            r=user_vals + [user_vals[0]],
            theta=dim_labels + [dim_labels[0]],
            fill="toself",
            name="Your organization",
            line=dict(color=tier_c),
            fillcolor=_hex_to_rgba(tier_c, 0.2),
        ))
        radar_fig.update_layout(
            polar=dict(
                bgcolor="#EBF0F8",
                radialaxis=dict(
                    visible=True, range=[0, 4], tickvals=[1,2,3,4],
                    ticktext=["1 Early","2 Developing","3 Advanced","4 Native"],
                    gridcolor="#CDD4E8", linecolor="#CDD4E8",
                    tickfont=dict(color="#8C7F74", size=10),
                ),
                angularaxis=dict(gridcolor="#CDD4E8", linecolor="#CDD4E8",
                                 tickfont=dict(color="#2D2926", size=11)),
            ),
            showlegend=True,
            legend=dict(orientation="h", y=-0.15, font=dict(color="#2D2926")),
            height=380,
            margin=dict(l=60, r=60, t=40, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#2D2926"),
        )
        st.plotly_chart(radar_fig, use_container_width=True)

        # ── Sector context ────────────────────────────────────────────────────
        st.markdown("#### Sector context")
        st.markdown(br.get("sector_context", ""))

        conf = br.get("data_confidence", "medium")
        conf_colors = {"high": "#4fc98e", "medium": "#f7a24f", "low": "#e74c3c"}
        st.caption(
            f"Benchmark data confidence: "
            f"<span style='color:{conf_colors.get(conf, '#aaa')}; font-weight:600'>"
            f"{conf.upper()}</span>",
            unsafe_allow_html=True,
        )

        # ── Dimension breakdown ───────────────────────────────────────────────
        st.divider()
        st.markdown("#### Dimension breakdown")
        dims_data = br.get("dimension_assessments", {})
        for dim_key, (dim_label, _) in DIMENSIONS.items():
            da = dims_data.get(dim_key, {})
            score = da.get("score", dim_scores[dim_key])
            gap_text = da.get("gap", "")
            bench_text = da.get("benchmark", "")
            # Color by score
            s_color = ["#e74c3c", "#f7a24f", "#4f8ef7", "#4fc98e"][score - 1]
            with st.expander(
                f"**{dim_label}** — score {score}/4 · {DIMENSIONS[dim_key][1][score-1]}"
            ):
                dc1, dc2 = st.columns([1, 2])
                with dc1:
                    st.markdown(
                        f"<div style='padding:10px; border-left:4px solid {s_color}; "
                        f"background:{s_color}18; border-radius:4px;'>"
                        f"<div style='font-size:11px; color:#888'>Your score</div>"
                        f"<div style='font-size:22px; font-weight:700; color:{s_color}'>{score}/4</div>"
                        f"<div style='font-size:12px; color:#aaa'>{DIMENSIONS[dim_key][1][score-1]}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with dc2:
                    st.markdown(f"**Sector benchmark:** {bench_text}")
                    st.markdown(f"**Gap analysis:** {gap_text}")

        # ── Strengths ─────────────────────────────────────────────────────────
        strengths = br.get("strengths", [])
        if strengths:
            st.divider()
            st.markdown("#### ✅ Where you're ahead")
            for s in strengths:
                st.markdown(f"- {s}")

        # ── Priority gaps ─────────────────────────────────────────────────────
        st.divider()
        st.markdown("#### ⚡ Priority gaps to close")
        for i, gap in enumerate(br.get("priority_gaps", []), 1):
            with st.expander(f"**#{i}: {gap.get('dimension', '')}**"):
                st.markdown(f"**Why it matters:** {gap.get('why_it_matters', '')}")
                st.success(f"**Recommended action:** {gap.get('action', '')}", icon="▶️")

        # ── Sector leaders note ───────────────────────────────────────────────
        leaders_note = br.get("sector_leaders_note", "")
        if leaders_note:
            st.divider()
            st.markdown("#### 🏆 Sector leaders context")
            st.markdown(leaders_note)

        st.divider()
        st.caption(
            "Benchmarks draw on: McKinsey Global AI Survey · BCG AI Maturity Report · "
            "Gartner AI Adoption Surveys · IBM IBV · Stanford HAI AI Index · "
            "Analysis by Claude (Anthropic) · "
            "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com), PMP · CPMAI"
        )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE A ROLE
# ════════════════════════════════════════════════════════════════════════════════
with tab_analyze:

    # Load GovAI industry map (cached, fetched once)
    industry_map = get_industry_occupation_map()
    govai_loaded = bool(industry_map)

    # Build an index: preset_key → industry_group for quick lookup
    _preset_by_group: dict[str, list[str]] = {}
    for pk, pv in PRESETS.items():
        g = pv.get("industry_group", "Other")
        _preset_by_group.setdefault(g, []).append(pk)

    col_input, col_spacer = st.columns([2, 1])

    with col_input:
        st.markdown("#### Select a role to analyze")

        # ── Step 1: Industry group ────────────────────────────────────────────
        if govai_loaded:
            all_groups = sorted(industry_map.keys())
        else:
            # Fallback: use preset industry groups only
            all_groups = sorted({p["industry_group"] for p in PRESETS.values()})

        industry_group = st.selectbox(
            "Industry",
            ["— select an industry —"] + all_groups,
            help="Filter roles by industry to narrow the list below.",
        )

        # ── Step 2: Role ──────────────────────────────────────────────────────
        CUSTOM_LABEL = "✏️  Enter a custom role..."
        EMPTY_LABEL = "— select a role —"

        if industry_group != "— select an industry —":
            # Presets for this industry group → featured at the top
            featured_presets = _preset_by_group.get(industry_group, [])
            featured_options = [f"⭐ {pk}" for pk in featured_presets]

            # GovAI occupations for this group
            govai_options = industry_map.get(industry_group, []) if govai_loaded else []

            role_options = (
                [EMPTY_LABEL]
                + featured_options
                + ([CUSTOM_LABEL] if not govai_loaded else [])
                + govai_options
                + ([CUSTOM_LABEL] if govai_loaded else [])
            )
        else:
            role_options = [EMPTY_LABEL, CUSTOM_LABEL]

        selected_role_option = st.selectbox(
            "Role / job title",
            role_options,
            help=(
                "⭐ = featured examples with pre-filled context. "
                "Other options are occupations from the GovAI/Manning-Aguirre dataset."
            ),
        )

        # ── Resolve role → preset or GovAI occupation ─────────────────────────
        active_preset: dict | None = None
        is_govai_occupation = False
        role = ""

        if selected_role_option.startswith("⭐ "):
            preset_key = selected_role_option[2:].strip()
            active_preset = PRESETS.get(preset_key)
            if active_preset:
                role = active_preset["role"]
                is_govai_occupation = False

        elif selected_role_option not in (EMPTY_LABEL, CUSTOM_LABEL):
            # Direct GovAI occupation selected
            role = selected_role_option
            is_govai_occupation = True

        # ── Custom role text input ─────────────────────────────────────────────
        custom_role = ""
        if selected_role_option == CUSTOM_LABEL or (
            selected_role_option == EMPTY_LABEL and not active_preset
        ):
            custom_role = st.text_input(
                "Custom role",
                placeholder="e.g. Data Analyst, School Principal, HR Manager",
            )
            role = custom_role.strip()

        # ── Hourly rate ────────────────────────────────────────────────────────
        if active_preset:
            default_rate = active_preset["hourly_rate"]
        elif industry_group != "— select an industry —":
            default_rate = INDUSTRY_RATE_DEFAULTS.get(industry_group, 75)
        else:
            default_rate = 75

        hourly_rate = st.number_input(
            "Fully-loaded hourly rate (USD)",
            min_value=20,
            max_value=500,
            value=default_rate,
            step=5,
        )

        # ── Context ────────────────────────────────────────────────────────────
        default_context = active_preset["context"] if active_preset else ""
        context = st.text_area(
            "Additional context (optional)",
            value=default_context,
            height=100,
            placeholder="Describe key workflows, tools used, pain points, or team size...",
        )

        # ── Usage limit ────────────────────────────────────────────────────────
        MAX_ANALYSES = 5
        if "analyses_used" not in st.session_state:
            st.session_state["analyses_used"] = 0

        used = st.session_state["analyses_used"]
        remaining = MAX_ANALYSES - used

        if remaining > 0:
            st.markdown(_usage_pill(used, MAX_ANALYSES, "analyses"), unsafe_allow_html=True)
        else:
            st.warning(
                "You've used all 5 free analyses for this session. "
                "Interested in unlimited access or a custom build for your organization? "
                "[Get in touch.](mailto:eldredgemc2@gmail.com)",
                icon="💡",
            )

        analyze = st.button(
            "Analyze role →",
            type="primary",
            disabled=not role.strip() or remaining <= 0,
        )

    # ── Analysis ───────────────────────────────────────────────────────────────
    if analyze and role.strip():
        # Determine industry string to send to Claude
        claude_industry = (
            active_preset["industry"]
            if active_preset
            else (industry_group if industry_group != "— select an industry —" else "")
        )
        with st.spinner(f"Analyzing '{role}' using PMI/CPMAI framework..."):
            try:
                result = classify_role(
                    role=role.strip(),
                    industry=claude_industry,
                    context=context.strip(),
                    hourly_rate=float(hourly_rate),
                )
                st.session_state["last_result"] = result
                st.session_state["last_role"] = role.strip()
                st.session_state["last_industry"] = claude_industry
                st.session_state["last_is_govai"] = is_govai_occupation
                st.session_state["last_govai_title"] = role.strip() if is_govai_occupation else None
                st.session_state["analyses_used"] = st.session_state.get("analyses_used", 0) + 1
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

    # ── Results ────────────────────────────────────────────────────────────────
    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        tasks = result.get("tasks", [])
        roi = result.get("roi_summary", {})
        _last_role = st.session_state.get("last_role", "")
        _last_industry = st.session_state.get("last_industry", "")
        _is_govai = st.session_state.get("last_is_govai", False)
        _govai_title = st.session_state.get("last_govai_title")

        st.divider()
        st.markdown(f"### Results: {result.get('role', _last_role)}")
        st.markdown(f"*{result.get('summary', '')}*")

        # ── ROI summary cards ─────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tasks analyzed", len(tasks))
        c2.metric("Weekly hours reviewed", f"{roi.get('total_weekly_hours_analyzed', 0):.0f} hrs")
        c3.metric("Weekly hours recoverable", f"{roi.get('total_weekly_hours_saved', 0):.1f} hrs")
        c4.metric(
            "Est. annual value",
            f"${roi.get('total_annual_savings', 0):,.0f}",
            help=f"Based on ${roi.get('hourly_rate', 0):.0f}/hr × hours saved × 52 weeks",
        )

        # ── In-page nav ───────────────────────────────────────────────────────
        st.markdown(
            "<div style='margin: 12px 0 4px; font-size:13px; color:#888;'>"
            "Jump to: "
            "<a href='#ai-vulnerability-assessment'>AI Vulnerability</a> &nbsp;·&nbsp; "
            "<a href='#category-breakdown'>Category breakdown</a> &nbsp;·&nbsp; "
            "<a href='#task-by-task-analysis'>Task table</a> &nbsp;·&nbsp; "
            "<a href='#implementation-roadmap'>Roadmap</a>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── GovAI Vulnerability Panel ─────────────────────────────────────────
        if _is_govai and _govai_title:
            govai = lookup_by_title(_govai_title)
        else:
            govai = lookup_occupation(_last_role, _last_industry)

        if govai and govai["match_score"] >= 0.25:
            exp_pct = govai["ai_exposure_pct"] * 100
            ac_pct = govai["adaptive_capacity"] * 100
            exposure_raw = govai["ai_exposure"] * 100
            is_vuln = govai["is_vulnerable"]

            vuln_color = "#e74c3c" if is_vuln else "#2ecc71"
            vuln_label = "⚠️ Elevated vulnerability" if is_vuln else "✅ Lower vulnerability"
            vuln_explain = (
                "High AI exposure + low adaptive capacity"
                if is_vuln
                else "Either low AI exposure or strong adaptive capacity"
            )

            st.markdown("#### AI Vulnerability Assessment")
            st.markdown(
                f"<small>Matched to: <em>{govai['matched_occupation']}</em>"
                + (f" (similarity {govai['match_score']:.0%})" if govai["match_score"] < 1.0 else "")
                + " · Source: Manning & Aguirre (2025) / GovAI · NBER w34705</small>",
                unsafe_allow_html=True,
            )

            vc1, vc2, vc3, vc4 = st.columns(4)
            vc1.metric(
                "AI Exposure",
                f"{exposure_raw:.0f}%",
                help=(
                    "Share of work tasks exposed to AI (Eloundou et al. 2024, human assessment). "
                    "E1 + 50% × E2 formulation."
                ),
            )
            vc2.metric(
                "Exposure Percentile",
                f"{exp_pct:.0f}th",
                help="How this occupation ranks vs. all 356 occupations in the dataset.",
            )
            vc3.metric(
                "Adaptive Capacity",
                f"{ac_pct:.0f}th pctile",
                help=(
                    "Occupation's ability to navigate job transitions if displaced. "
                    "Combines skill transferability, net liquid wealth, geographic density, "
                    "and age composition (Manning & Aguirre 2025, main spec)."
                ),
            )
            vc4.markdown(
                f"<div style='padding:12px 0 4px'>"
                f"<div style='font-size:12px; color:#888; margin-bottom:4px'>Vulnerability</div>"
                f"<div style='font-size:15px; font-weight:700; color:{vuln_color}'>{vuln_label}</div>"
                f"<div style='font-size:11px; color:#aaa; margin-top:4px'>{vuln_explain}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Compute our own hours-based vulnerability %
            llm_auto_tasks = [
                t for t in tasks if t.get("category") in ("LLM", "Automation", "Traditional ML")
            ]
            total_hours = sum(t.get("weekly_hours", 0) for t in tasks)
            our_vuln_pct = (
                sum(t.get("weekly_hours", 0) for t in llm_auto_tasks) / total_hours * 100
                if total_hours else 0
            )

            with st.expander("📊 How these scores compare"):
                st.markdown(
                    f"**GovAI AI exposure score: {exposure_raw:.0f}%** — "
                    f"the research team assessed what share of this occupation's tasks "
                    f"fall into GPT-4-level exposure categories.\n\n"
                    f"**Our task-level analysis: {our_vuln_pct:.0f}% of weekly hours** are in "
                    f"AI-automatable categories (LLM, Traditional ML, or Automation) "
                    f"based on Claude's breakdown above.\n\n"
                    f"The two measures capture different things: the GovAI score reflects "
                    f"*potential exposure* across all workers in the occupation; our analysis "
                    f"reflects *which specific tasks* are actionable starting points for "
                    f"AI adoption in this role. The gap between them is a consulting "
                    f"conversation — where does the real opportunity lie?\n\n"
                    f"**Adaptive capacity ({ac_pct:.0f}th percentile)** measures how well "
                    f"workers in this occupation could navigate a job transition if displaced: "
                    f"skill transferability, financial resilience, geographic mobility, and "
                    f"age composition. High exposure with high adaptive capacity = disruptive "
                    f"but manageable. High exposure with low adaptive capacity = the workers "
                    f"Manning & Aguirre flag as most at risk.\n\n"
                    f"*Source: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705) · "
                    f"[Replication data](https://github.com/t6aguirre/adaptive-capacity-index) (MIT) · "
                    f"AI exposure from [Eloundou et al. (2024)](https://doi.org/10.1126/science.adj0998)*"
                )

        elif govai_loaded:
            st.info(
                "ℹ️ GovAI data loaded but no close match found for this role. "
                "Try selecting a role from the dropdown for an exact match."
            )

        st.divider()

        # ── Category breakdown ────────────────────────────────────────────────
        st.markdown("#### Category breakdown")
        cat_counts: dict[str, int] = {}
        for t in tasks:
            c = t.get("category", "Unknown")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        cat_cols = st.columns(len(cat_counts))
        for i, (cat, count) in enumerate(sorted(cat_counts.items())):
            color = CATEGORY_COLORS.get(cat, "#999")
            cat_cols[i].markdown(
                f"<div style='padding:12px; border-left:4px solid {color}; "
                f"background:{color}11; border-radius:4px;'>"
                f"<strong style='color:{color}'>{cat}</strong><br/>"
                f"<span style='font-size:1.4em; font-weight:700'>{count}</span> tasks"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Task table ────────────────────────────────────────────────────────
        st.markdown("#### Task-by-task analysis")

        sort_by = st.radio(
            "Sort by:",
            ["Priority (Quick Wins first)", "Annual savings (highest first)", "Category"],
            horizontal=True,
        )

        df_tasks = pd.DataFrame(tasks)
        df_tasks["tools_str"] = df_tasks["tools"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else x
        )
        def _fmt_savings(row) -> str:
            if row.get("category") == "Human Only":
                return "Fundamental" if row.get("complexity") == "High" else "—"
            s = row.get("annual_savings", 0)
            return f"${s:,}" if s else "—"

        df_tasks["annual_savings_fmt"] = df_tasks.apply(_fmt_savings, axis=1)
        df_tasks["time_impact"] = df_tasks.apply(
            lambda r: f"{r['weekly_hours']} hrs/wk → save {r['hours_saved_weekly']}", axis=1
        )

        if sort_by == "Priority (Quick Wins first)":
            df_tasks["_psort"] = df_tasks["priority"].map(PRIORITY_ORDER).fillna(9)
            df_tasks["_csort"] = df_tasks["complexity"].map(COMPLEXITY_ORDER).fillna(9)
            df_tasks = df_tasks.sort_values(["_psort", "_csort"])
        elif sort_by == "Annual savings (highest first)":
            df_tasks = df_tasks.sort_values("annual_savings", ascending=False)
        else:
            df_tasks = df_tasks.sort_values("category")

        display_cols = [
            "task", "category", "rationale", "tools_str",
            "time_impact", "annual_savings_fmt", "priority", "complexity",
        ]
        col_labels = {
            "task": "Task",
            "category": "AI Method",
            "rationale": "Why this method",
            "tools_str": "Recommended tools",
            "time_impact": "Time impact",
            "annual_savings_fmt": "Est. annual value",
            "priority": "Priority",
            "complexity": "Complexity",
        }

        st.markdown(
            _render_task_table(df_tasks),
            unsafe_allow_html=True,
        )

        # ── Expandable task detail cards ──────────────────────────────────────
        st.divider()
        st.markdown("#### Task details")
        for t in (df_tasks.to_dict("records") if sort_by != "Category" else tasks):
            cat = t.get("category", "")
            color = CATEGORY_COLORS.get(cat, "#999")
            with st.expander(f"**{t['task']}** — {cat}"):
                dc1, dc2 = st.columns([2, 1])
                with dc1:
                    st.markdown(f"**Description:** {t.get('description', '')}")
                    st.markdown(f"**Why {cat}:** {t.get('rationale', '')}")
                    tools = t.get("tools", t.get("tools_str", ""))
                    if isinstance(tools, list):
                        tools = ", ".join(tools)
                    st.markdown(f"**Tools:** {tools}")
                with dc2:
                    st.metric("Weekly hours", t.get("weekly_hours", 0))
                    st.metric("AI reducible", f"{t.get('reducible_pct', 0)}%")
                    st.metric("Est. annual value", f"${t.get('annual_savings', 0):,}")
                    st.markdown(
                        f"**Priority:** {t.get('priority', '')} &nbsp;|&nbsp; "
                        f"**Complexity:** {t.get('complexity', '')}",
                        unsafe_allow_html=True,
                    )

        # ── Implementation notes ──────────────────────────────────────────────
        st.divider()
        st.markdown("#### Implementation roadmap")
        st.info(result.get("implementation_notes", ""))

        # ── Quick wins callout ────────────────────────────────────────────────
        quick_wins = [t for t in tasks if t.get("priority") == "Quick Win"]
        if quick_wins:
            st.markdown("**Recommended starting points (Quick Wins):**")
            for qw in quick_wins:
                tools = qw.get("tools", [])
                tools_str = ", ".join(tools[:2]) if isinstance(tools, list) else str(tools)
                st.markdown(
                    f"- **{qw['task']}** ({qw['category']}) — "
                    f"saves ~{qw['hours_saved_weekly']} hrs/wk · tools: {tools_str}"
                )

    # ── Human + Machine CTA ──────────────────────────────────────────────────
    if "last_result" in st.session_state:
        st.markdown(
            "<div style='"
            "margin-top:2rem;padding:28px 32px;"
            "background:#0a1240;"
            "border-left:4px solid #eeb840;"
            "border-radius:10px;"
            "'>"
            "<p style='"
            "margin:0 0 10px;"
            "font-size:11.5px;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.1em;"
            "color:#eeb840;"
            "'>Ready to act on this?</p>"
            "<p style='"
            "margin:0 0 20px;"
            "color:rgba(255,255,255,0.85);"
            "font-size:16px;line-height:1.65;"
            "'>"
            "This analysis took 30 seconds. Turning it into a "
            "<strong style='color:#fff;'>"
            "work plan that centers around lots of humans and lots of machines "
            "working together to accomplish your goals"
            "</strong>"
            " takes a conversation."
            "</p>"
            "<a href='mailto:eldredgemc2@gmail.com"
            "?subject=WorkAI%20Compass%20%E2%80%94%20let%27s%20talk' "
            "style='"
            "display:inline-block;padding:10px 22px;"
            "background:#eeb840;color:#0a1240;"
            "font-weight:700;font-size:14px;"
            "border-radius:7px;text-decoration:none;"
            "'>"
            "Start the conversation &rarr;"
            "</a>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Methodology: [PMI CPMAI](https://www.pmi.org/certifications/ai-project-management-cpmai) · "
        "AI analysis: Claude (Anthropic) · "
        "Vulnerability data: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705) / GovAI · "
        "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com), PMP · CPMAI · "
        "[Request source access](mailto:eldredgemc2@gmail.com?subject=WorkAI%20Compass%20%E2%80%94%20source%20code%20request)"
    )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — EXPLORE ALL OCCUPATIONS (SCATTER / HEAT MAP)
# ════════════════════════════════════════════════════════════════════════════════
with tab_explore:
    st.markdown("### AI Vulnerability: All 356 Occupations")
    st.markdown(
        "Each point is one of 356 occupations from the Manning & Aguirre (2025) dataset. "
        "**Right** = more AI-exposed. **Up** = more adaptive capacity. "
        "Occupations in the **bottom-right quadrant** face the highest potential vulnerability: "
        "high exposure to AI disruption, low ability to absorb the transition."
    )

    scatter_df = get_scatter_data()

    if scatter_df is None:
        st.warning(
            "Could not load GovAI occupation data. "
            "Check your internet connection and try refreshing."
        )
    else:
        # ── Filters ───────────────────────────────────────────────────────────
        fe1, fe2 = st.columns([2, 1])
        with fe1:
            all_groups_scatter = sorted(scatter_df["industry_group"].unique())
            selected_groups = st.multiselect(
                "Filter by industry group",
                all_groups_scatter,
                default=[],
                placeholder="All industries shown — select to filter",
            )
        with fe2:
            highlight_title = None
            if "last_govai_title" in st.session_state and st.session_state["last_govai_title"]:
                highlight_title = st.session_state["last_govai_title"]
            elif "last_result" in st.session_state:
                # Try to find the matched GovAI occupation
                _r = st.session_state["last_result"]
                _govai = lookup_occupation(
                    st.session_state.get("last_role", ""),
                    st.session_state.get("last_industry", ""),
                )
                if _govai:
                    highlight_title = _govai["matched_occupation"]

            if highlight_title:
                st.info(f"📍 Highlighted: *{highlight_title}*", icon=None)

        plot_df = (
            scatter_df[scatter_df["industry_group"].isin(selected_groups)]
            if selected_groups
            else scatter_df
        )

        # ── Plotly scatter ────────────────────────────────────────────────────
        fig = px.scatter(
            plot_df,
            x="ai_exposure_pct",
            y="adaptive_capacity_pct",
            color="industry_group",
            hover_name="description",
            hover_data={
                "ai_exposure_pct": ":.1f",
                "adaptive_capacity_pct": ":.1f",
                "employment_fmt": True,
                "industry_group": False,
            },
            labels={
                "ai_exposure_pct": "AI Exposure (%)",
                "adaptive_capacity_pct": "Adaptive Capacity (percentile)",
                "employment_fmt": "Employment",
            },
            opacity=0.75,
            height=580,
            color_discrete_sequence=px.colors.qualitative.Plotly,
        )

        # Quadrant lines
        fig.add_vline(x=50, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
        fig.add_hline(y=35, line_dash="dot", line_color="rgba(220,80,80,0.4)", line_width=1)

        # Quadrant labels
        fig.add_annotation(
            x=88, y=8, text="⚠️ Vulnerable zone",
            showarrow=False, font=dict(size=11, color="rgba(200,60,60,0.9)"),
            bgcolor="rgba(230,235,245,0.85)",
        )
        fig.add_annotation(
            x=12, y=90, text="✅ Lower risk",
            showarrow=False, font=dict(size=11, color="rgba(30,140,70,0.9)"),
            bgcolor="rgba(230,235,245,0.85)",
        )
        fig.add_annotation(
            x=88, y=90, text="High exposure,\nstrong adaptive capacity",
            showarrow=False, font=dict(size=10, color="rgba(80,80,80,0.8)"),
            bgcolor="rgba(230,235,245,0.85)",
            align="center",
        )

        # Highlight the currently analyzed occupation if available
        if highlight_title:
            hl = scatter_df[scatter_df["description"].str.lower() == highlight_title.lower()]
            if not hl.empty:
                fig.add_trace(go.Scatter(
                    x=hl["ai_exposure_pct"],
                    y=hl["adaptive_capacity_pct"],
                    mode="markers",
                    marker=dict(size=18, color="#eeb840", line=dict(color="#0a1240", width=2)),
                    name="Currently analyzed",
                    hovertext=hl["description"],
                    hoverinfo="text",
                ))

        fig.update_layout(
            legend=dict(title="Industry Group", orientation="v", x=1.01, y=1),
            xaxis=dict(title="AI Exposure (% of tasks)", range=[-2, 102],
                       gridcolor="#CDD4E8", linecolor="#CDD4E8"),
            yaxis=dict(title="Adaptive Capacity (percentile)", range=[-2, 102],
                       gridcolor="#CDD4E8", linecolor="#CDD4E8"),
            margin=dict(l=60, r=220, t=30, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#EBF0F8",
            font=dict(family="Inter, sans-serif", color="#2D2926"),
        )
        fig.update_traces(marker_size=8, selector=dict(mode="markers"))

        st.plotly_chart(fig, use_container_width=True)

        # ── Summary stats ─────────────────────────────────────────────────────
        vuln_count = int(((plot_df["ai_exposure_pct"] >= 50) & (plot_df["adaptive_capacity_pct"] <= 35)).sum())
        total_emp_vuln = plot_df[
            (plot_df["ai_exposure_pct"] >= 50) & (plot_df["adaptive_capacity_pct"] <= 35)
        ]["total_emp"].sum()
        total_emp_all = plot_df["total_emp"].sum()

        sv1, sv2, sv3 = st.columns(3)
        sv1.metric("Occupations shown", len(plot_df))
        sv2.metric("In vulnerable zone", f"{vuln_count} occupations")
        sv3.metric(
            "Employment in vulnerable zone",
            f"{total_emp_vuln / 1e6:.1f}M" if total_emp_vuln > 0 else "—",
            help="Total BLS employment across occupations in the bottom-right quadrant.",
        )

        st.divider()

        with st.expander("📋 Data sources & freshness"):
            st.markdown(
                """
| Source | What it provides | Vintage | Update cadence | License |
|---|---|---|---|---|
| [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705), NBER w34705 | AI exposure scores + adaptive capacity index for 356 occupations | Published Jan 2026 | Static research snapshot; app re-fetches from GitHub hourly | [MIT](https://github.com/t6aguirre/adaptive-capacity-index/blob/main/LICENSE) |
| [Eloundou et al. (2024)](https://doi.org/10.1126/science.adj0998), *Science* | Underlying GPT-4 task-level exposure ratings (E1/E2) that feed the AI exposure column | Published 2024 | Static | Academic |
| [BLS OEWS](https://www.bls.gov/oes/) | Employment counts (`total_emp`) incorporated into the Manning & Aguirre dataset | May 2023 (as used in paper) | BLS releases annually each May | Public domain |
| [BLS Employment Projections 2024–34](https://www.bls.gov/emp/) | Projected occupation growth through 2034 (not yet integrated) | Released 2025 | Every 2 years | Public domain |

**A note on freshness:** The AI exposure and adaptive capacity scores are research snapshots, not live feeds.
They represent the best available academic measurement as of early 2026. The next comparable dataset
would likely come from a future paper or an updated BLS projections cycle (~2027).
The chart auto-refreshes from the source repository — if the authors push a data update,
this app reflects it within the hour.
                """
            )

        st.caption(
            "Data: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705), NBER w34705 · "
            "[Replication data](https://github.com/t6aguirre/adaptive-capacity-index) (MIT License) · "
            "AI exposure: [Eloundou et al. (2024)](https://doi.org/10.1126/science.adj0998) · "
            "Quadrant threshold: x=50% exposure, y=35th pctile adaptive capacity"
        )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT
# ════════════════════════════════════════════════════════════════════════════════
with tab_about:

    # ── Mission ───────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='max-width:720px; margin: 0 auto 2rem auto; text-align:center;'>"
        "<h2 style='font-size:2rem; line-height:1.3; margin-bottom:1rem;'>"
        "AI is moving fast. The data is out there.<br/>"
        "<span style='color:#4f8ef7;'>WorkAI Compass helps you use it.</span>"
        "</h2>"
        "<p style='font-size:1.1rem; color:#888; line-height:1.7;'>"
        "Every week brings new AI headlines — breakthroughs, warnings, and predictions that "
        "seem to contradict each other. WorkAI Compass cuts through the noise with "
        "peer-reviewed research, government labor data, and AI analysis to give you "
        "a grounded, practical picture of what's actually happening."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Three lenses ──────────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='text-align:center; margin-bottom:1.5rem;'>Three lenses, one tool</h3>",
        unsafe_allow_html=True,
    )

    lens1, lens2, lens3 = st.columns(3)

    def _lens_card(icon, title, body, tab_name, color):
        return (
            f"<div style='padding:20px; border-top:3px solid {color}; "
            f"background:{color}0d; border-radius:6px; height:100%;'>"
            f"<div style='font-size:2rem; margin-bottom:8px'>{icon}</div>"
            f"<h4 style='margin:0 0 8px; color:{color}'>{title}</h4>"
            f"<p style='font-size:0.9rem; color:#aaa; margin-bottom:10px; line-height:1.6'>{body}</p>"
            f"<span style='font-size:11px; background:{color}22; color:{color}; "
            f"padding:3px 8px; border-radius:12px;'>{tab_name}</span>"
            f"</div>"
        )

    with lens1:
        st.markdown(
            _lens_card(
                "🎯", "Your role",
                "Select any job title and get a task-by-task breakdown of where AI can help, "
                "what tools to consider, and what's worth protecting as uniquely human. "
                "Grounded in the PMI CPMAI framework and real occupational data.",
                "Analyze a Role tab",
                "#4f8ef7",
            ),
            unsafe_allow_html=True,
        )

    with lens2:
        st.markdown(
            _lens_card(
                "💼", "Your company",
                "Two tools for organizational decision-makers: an AI investment brief "
                "tailored to your industry, company type, and size — and an adoption "
                "benchmark that shows where you stand relative to sector peers, "
                "with specific gaps and priority actions.",
                "Executive AI Brief · AI Adoption Benchmark",
                "#4fc98e",
            ),
            unsafe_allow_html=True,
        )

    with lens3:
        st.markdown(
            _lens_card(
                "🗺️", "The bigger picture",
                "Explore 356 occupations from peer-reviewed NBER research, plotted by "
                "AI exposure and adaptive capacity. See which roles and industries face "
                "the greatest structural risk — and how different sectors compare.",
                "Explore All Occupations tab",
                "#f7a24f",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Who it's for ──────────────────────────────────────────────────────────
    st.markdown("### Who it's for")
    aud1, aud2 = st.columns(2)

    with aud1:
        st.markdown(
            """
**Executives and business leaders** — CEOs, CFOs, and operations leaders who need a
clear-eyed view of where AI investment will pay off for their specific organization,
and how their adoption posture compares to competitors. Not a vendor pitch. No hype.

**HR and talent professionals** — workforce planners and people leaders thinking about
which roles are most affected, which skills need investment, and how to communicate
AI's impact honestly with employees.
            """
        )

    with aud2:
        st.markdown(
            """
**Individual professionals** — anyone wondering how AI will change their own job.
The role analyzer gives you a concrete, task-level answer specific to your field —
not a generic "AI will automate X% of jobs" headline.

**AI enthusiasts and practitioners** — people who follow the research and want an
interactive interface to the best publicly available occupational AI data, without
building it themselves.
            """
        )

    st.divider()

    # ── What makes it different ───────────────────────────────────────────────
    st.markdown("### What makes it different")
    diff1, diff2, diff3 = st.columns(3)

    def _pillar(title, body):
        return (
            f"<div style='padding:16px; background:rgba(79,142,247,0.06); "
            f"border-radius:6px; height:100%'>"
            f"<h4 style='margin:0 0 8px'>{title}</h4>"
            f"<p style='font-size:0.88rem; color:#aaa; line-height:1.6; margin:0'>{body}</p>"
            f"</div>"
        )

    with diff1:
        st.markdown(
            _pillar(
                "Data-first, not vendor-first",
                "Every analysis draws on peer-reviewed research (NBER, Science journal), "
                "U.S. government labor statistics, and the PMI CPMAI professional framework — "
                "not a vendor's marketing claims about their own product."
            ),
            unsafe_allow_html=True,
        )

    with diff2:
        st.markdown(
            _pillar(
                "Specific, not generic",
                "The answers change meaningfully depending on your industry, company size, "
                "and role. A 40-person nonprofit and a 5,000-person bank get very different "
                "analyses — because they should."
            ),
            unsafe_allow_html=True,
        )

    with diff3:
        st.markdown(
            _pillar(
                "Honest about limits",
                "Each tool tells you what data it's drawing on, how current that data is, "
                "and where the analysis is uncertain. The goal is to help you think clearly, "
                "not to give you false confidence."
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Data & methodology ────────────────────────────────────────────────────
    st.markdown("### Data & methodology")
    st.markdown(
        """
WorkAI Compass combines four independent sources:

**Manning & Aguirre (2025)** — "How Adaptable Are American Workers to AI-Induced Job
Displacement?" NBER Working Paper 34705. Covers 356 occupations with AI exposure scores
(from Eloundou et al., *Science* 2024) and an original adaptive capacity index measuring
workers' ability to navigate displacement: skill transferability, financial resilience,
geographic mobility, and age composition. MIT-licensed replication data.

**PMI CPMAI task taxonomy** — The Project Management Institute's Certified AI Project
Manager framework classifies AI work into four delivery methods: LLM, Traditional ML,
Automation, and Human Only. Used as the analytical backbone of the role analyzer.

**BLS Occupational Employment and Wage Statistics (OEWS)** — Employment counts
incorporated into the Manning & Aguirre dataset. Updated annually by the Bureau of
Labor Statistics.

**Claude (Anthropic)** — The role analysis, executive brief, and benchmarking reports
are generated by Claude using the above data as grounding context. All AI-generated
analysis includes source attribution. The app runs on `claude-sonnet-4-6` by default;
the Executive AI Brief tab offers `claude-opus-4-6` for more thorough analysis.
        """
    )

    st.divider()

    # ── About the builder ─────────────────────────────────────────────────────
    st.markdown("### About the builder")
    ab1, ab2 = st.columns([2, 1])

    with ab1:
        st.markdown(
            """
**Joseph Eldredge** is a program manager and AI strategy advisor based in Central Virginia,
working with small and mid-sized organizations navigating complex technology decisions.
He holds a PMP (Project Management Professional) and CPMAI (Certified AI Project Manager)
certification, and has delivered programs spanning federal contracting, financial services,
nonprofit operations, and public sector technology.

WorkAI Compass is a working demonstration of the kind of analysis he brings to client
engagements — built in public, grounded in real data, and designed to be genuinely useful
rather than just impressive.
            """
        )
        st.markdown(
            "📧 [eldredgemc2@gmail.com](mailto:eldredgemc2@gmail.com) &nbsp;·&nbsp; "
            "🌐 [eldredgemgmtconsulting.com](https://eldredgemgmtconsulting.com) &nbsp;·&nbsp; "
            "💻 [Request source access](mailto:eldredgemc2@gmail.com?subject=WorkAI%20Compass%20%E2%80%94%20source%20code%20request)",
            unsafe_allow_html=True,
        )

    with ab2:
        st.markdown(
            "<div style='padding:16px; background:rgba(79,201,142,0.08); "
            "border:1px solid rgba(79,201,142,0.2); border-radius:8px;'>"
            "<p style='font-size:0.85rem; color:#aaa; line-height:1.7; margin:0;'>"
            "Need a custom version of this for your organization? "
            "A tailored workforce AI assessment, an internal tool for your team, "
            "or an executive workshop grounded in your actual data? "
            "<a href='mailto:eldredgemc2@gmail.com' style='color:#4fc98e;'>Get in touch.</a>"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )
