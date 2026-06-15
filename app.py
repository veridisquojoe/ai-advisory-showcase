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
import plotly.express as px
import plotly.graph_objects as go

from src.classifier import classify_role
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
    "Classify any role's tasks by AI approach — using the "
    "[PMI/CPMAI](https://www.pmi.org/certifications/ai-project-management-cpmai) "
    "taxonomy — with tool recommendations, ROI estimates, and occupation-level "
    "AI vulnerability data from Manning & Aguirre (2025) / GovAI."
)

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

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_analyze, tab_explore = st.tabs(["🎯 Analyze a Role", "🗺️ Explore All Occupations"])


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

        analyze = st.button(
            "Analyze role →",
            type="primary",
            disabled=not role.strip(),
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
        df_tasks["annual_savings_fmt"] = df_tasks["annual_savings"].apply(lambda x: f"${x:,}")
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

        styled = (
            df_tasks[display_cols]
            .rename(columns=col_labels)
            .style.map(color_category, subset=["AI Method"])
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

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

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Methodology: [PMI CPMAI](https://www.pmi.org/certifications/ai-project-management-cpmai) · "
        "AI analysis powered by Claude (Anthropic) · "
        "Vulnerability data: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705) / GovAI · "
        "Built by [Joseph Eldredge](https://eldredgemgmtconsulting.com), PMP · CPMAI"
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
            showarrow=False, font=dict(size=11, color="rgba(220,80,80,0.8)"),
            bgcolor="rgba(255,255,255,0.6)",
        )
        fig.add_annotation(
            x=12, y=90, text="✅ Lower risk",
            showarrow=False, font=dict(size=11, color="rgba(40,160,80,0.8)"),
            bgcolor="rgba(255,255,255,0.6)",
        )
        fig.add_annotation(
            x=88, y=90, text="High exposure,\nstrong adaptive capacity",
            showarrow=False, font=dict(size=10, color="rgba(100,100,100,0.7)"),
            bgcolor="rgba(255,255,255,0.6)",
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
            xaxis=dict(title="AI Exposure (% of tasks)", range=[-2, 102]),
            yaxis=dict(title="Adaptive Capacity (percentile)", range=[-2, 102]),
            margin=dict(l=60, r=220, t=30, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,248,248,0.5)",
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
        st.caption(
            "Data: [Manning & Aguirre (2025)](https://www.nber.org/papers/w34705), NBER w34705 · "
            "[Replication data](https://github.com/t6aguirre/adaptive-capacity-index) (MIT License) · "
            "AI exposure: [Eloundou et al. (2024)](https://doi.org/10.1126/science.adj0998) · "
            "Quadrant threshold: x=50% exposure, y=35th pctile adaptive capacity"
        )
