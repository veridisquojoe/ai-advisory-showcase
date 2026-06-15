"""
app.py
------
AI Advisory Showcase — Task Classifier & ROI Estimator
Built on the PMI/CPMAI AI task taxonomy by Joseph Eldredge

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
from src.classifier import classify_role
from src.presets import PRESETS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Task Advisor",
    page_icon="🧠",
    layout="wide",
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


# ── Header ────────────────────────────────────────────────────────────────────
st.title("🧠 AI Task Advisor")
st.caption(
    "Enter any role to see how AI can augment it — classified by the "
    "[PMI/CPMAI](https://www.pmi.org/certifications/artificial-intelligence-cpmai) "
    "AI task taxonomy with tool recommendations and ROI estimates."
)
st.divider()

# ── Sidebar: methodology ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### About this tool")
    st.markdown(
        "This advisor applies the **PMI CPMAI task classification framework** "
        "to break down any role into its component tasks and assess which AI "
        "approach fits each one.\n\n"
        "**Four categories:**\n\n"
        "🔵 **LLM** — language generation, summarization, Q&A, drafting\n\n"
        "🟠 **Traditional ML** — prediction, classification, anomaly detection\n\n"
        "🟢 **Automation** — rule-based, deterministic, scripted workflows\n\n"
        "⚪ **Human Only** — relationship, negotiation, ethical judgment"
    )
    st.divider()
    st.markdown(
        "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com) · "
        "PMP, CPMAI · AI advisory for SMBs and public sector organizations."
    )

# ── Input panel ───────────────────────────────────────────────────────────────
col_input, col_spacer = st.columns([2, 1])

with col_input:
    st.markdown("#### Analyze a role")

    preset_choice = st.selectbox(
        "Load a pre-built example or enter your own below:",
        ["— enter custom role —"] + list(PRESETS.keys()),
    )

    if preset_choice != "— enter custom role —":
        preset = PRESETS[preset_choice]
        default_role = preset["role"]
        default_industry = preset["industry"]
        default_rate = preset["hourly_rate"]
        default_context = preset["context"]
    else:
        default_role = ""
        default_industry = ""
        default_rate = 75
        default_context = ""

    role = st.text_input("Role / job title", value=default_role, placeholder="e.g. HR Manager, Loan Officer, DevOps Engineer")
    industry = st.text_input("Industry (optional)", value=default_industry, placeholder="e.g. Healthcare, Financial Services")
    hourly_rate = st.number_input("Fully-loaded hourly rate (USD)", min_value=20, max_value=500, value=default_rate, step=5)
    context = st.text_area(
        "Additional context (optional)",
        value=default_context,
        height=100,
        placeholder="Describe key workflows, tools used, pain points, or team size...",
    )

    analyze = st.button("Analyze role →", type="primary", disabled=not role.strip())

# ── Results ───────────────────────────────────────────────────────────────────
if analyze and role.strip():
    with st.spinner(f"Analyzing '{role}' using PMI/CPMAI framework..."):
        try:
            result = classify_role(
                role=role.strip(),
                industry=industry.strip(),
                context=context.strip(),
                hourly_rate=float(hourly_rate),
            )
            st.session_state["last_result"] = result
            st.session_state["last_role"] = role.strip()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

# Render from session state so results persist across widget interactions
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    tasks = result.get("tasks", [])
    roi = result.get("roi_summary", {})

    st.divider()
    st.markdown(f"### Results: {result.get('role', role)}")
    st.markdown(f"*{result.get('summary', '')}*")

    # ── ROI summary cards ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasks analyzed", len(tasks))
    c2.metric("Weekly hours reviewed", f"{roi.get('total_weekly_hours_analyzed', 0):.0f} hrs")
    c3.metric("Weekly hours recoverable", f"{roi.get('total_weekly_hours_saved', 0):.1f} hrs")
    c4.metric(
        "Est. annual value",
        f"${roi.get('total_annual_savings', 0):,.0f}",
        help=f"Based on ${roi.get('hourly_rate', 0):.0f}/hr fully-loaded rate × hours saved × 52 weeks",
    )

    st.divider()

    # ── Category breakdown ────────────────────────────────────────────────────
    st.markdown("#### Category breakdown")
    cat_counts = {}
    for t in tasks:
        c = t.get("category", "Unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    cat_cols = st.columns(len(cat_counts))
    for i, (cat, count) in enumerate(sorted(cat_counts.items())):
        color = CATEGORY_COLORS.get(cat, "#999")
        cat_cols[i].markdown(
            f"<div style='padding:12px; border-left: 4px solid {color}; "
            f"background:{color}11; border-radius:4px;'>"
            f"<strong style='color:{color}'>{cat}</strong><br/>"
            f"<span style='font-size:1.4em; font-weight:700'>{count}</span> tasks"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Task table ────────────────────────────────────────────────────────────
    st.markdown("#### Task-by-task analysis")

    sort_by = st.radio(
        "Sort by:",
        ["Priority (Quick Wins first)", "Annual savings (highest first)", "Category"],
        horizontal=True,
    )

    df = pd.DataFrame(tasks)
    df["tools_str"] = df["tools"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    df["annual_savings_fmt"] = df["annual_savings"].apply(lambda x: f"${x:,}")
    df["time_impact"] = df.apply(
        lambda r: f"{r['weekly_hours']} hrs/wk → save {r['hours_saved_weekly']}", axis=1
    )

    if sort_by == "Priority (Quick Wins first)":
        df["_psort"] = df["priority"].map(PRIORITY_ORDER).fillna(9)
        df["_csort"] = df["complexity"].map(COMPLEXITY_ORDER).fillna(9)
        df = df.sort_values(["_psort", "_csort"])
    elif sort_by == "Annual savings (highest first)":
        df = df.sort_values("annual_savings", ascending=False)
    else:
        df = df.sort_values("category")

    display_cols = ["task", "category", "rationale", "tools_str", "time_impact", "annual_savings_fmt", "priority", "complexity"]
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

    styled = (
        df[display_cols]
        .rename(columns=col_labels)
        .style.map(color_category, subset=["AI Method"])
    )

    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # ── Expandable task detail cards ──────────────────────────────────────────
    st.divider()
    st.markdown("#### Task details")
    for t in (df.to_dict("records") if sort_by != "Category" else tasks):
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

    # ── Implementation notes ──────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Implementation roadmap")
    st.info(result.get("implementation_notes", ""))

    # ── Quick wins callout ────────────────────────────────────────────────────
    quick_wins = [t for t in tasks if t.get("priority") == "Quick Win"]
    if quick_wins:
        st.markdown("**Recommended starting points (Quick Wins):**")
        for qw in quick_wins:
            tools = qw.get("tools", [])
            if isinstance(tools, list):
                tools_str = ", ".join(tools[:2])
            else:
                tools_str = str(tools)
            st.markdown(
                f"- **{qw['task']}** ({qw['category']}) — "
                f"saves ~{qw['hours_saved_weekly']} hrs/wk · tools: {tools_str}"
            )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Methodology: [PMI Certified Professional in Managing AI (CPMAI)](https://www.pmi.org/certifications/artificial-intelligence-cpmai) · "
    "AI analysis powered by Claude (Anthropic) · "
    "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com), PMP · CPMAI"
)
