"""
benchmarker.py
--------------
Claude-powered AI adoption benchmarking for organizations.

Takes a 5-dimension self-assessment + company profile and returns:
  - Maturity tier (Low / Medium / High / AI Native)
  - Sector benchmark narrative (drawing on Claude's knowledge of McKinsey,
    BCG, Gartner, IBM IBV survey data)
  - Dimension-by-dimension gap analysis
  - Priority recommendations
"""

import os
import json
import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

# Dimension labels and scale descriptions for the prompt
DIMENSIONS = {
    "strategy":    ("AI Strategy & Leadership",   ["No AI strategy", "AI on the agenda", "Documented, C-suite owned", "Embedded in corporate OKRs"]),
    "data":        ("Data Readiness",             ["Siloed / poor quality", "Partially centralized", "Mostly clean & governed", "Cloud-native, ML-ready"]),
    "use_cases":   ("Deployed Use Cases",         ["0 in production", "1–3 in production", "4–10 in production", "10+ in production"]),
    "talent":      ("AI Talent & Skills",         ["No dedicated resources", "Training underway", "Dedicated roles/team", "AI CoE or embedded AI"]),
    "governance":  ("AI Governance & Ethics",     ["None", "Informal policies", "Formal documented policy", "Integrated into risk management"]),
}

SYSTEM_PROMPT = """You are a senior AI strategy advisor producing an AI adoption benchmarking report.
Your analysis draws on publicly available research — McKinsey Global AI Survey, BCG AI maturity
benchmarks, Gartner AI adoption surveys, IBM Institute for Business Value research, Stanford HAI
AI Index, and similar authoritative sources.

Guidelines:
- Be specific to the company's industry, size, and type — aggregate statistics vary significantly by sector.
- For large enterprises (500+ employees), you may reference publicly known AI initiatives at
  sector leaders to illustrate what "advanced" looks like in that industry.
- For smaller organizations, rely primarily on survey aggregate data and benchmarks.
- Be honest about what you know vs. estimate — distinguish between hard survey figures and qualitative judgment.
- Frame gaps constructively — the goal is to show a clear path to improvement, not just a score.
- Sector benchmarks should reflect where companies actually are, not aspirational ideals.

Always respond with valid JSON only. No markdown, no explanation outside the JSON structure."""

BENCHMARK_PROMPT = """Produce an AI adoption benchmarking report for the following organization profile:

Industry: {industry}
Company type: {company_type}
Company size: {company_size}
Additional context: {context}

Self-assessment scores (1=Early, 2=Developing, 3=Advanced, 4=Native):
- AI Strategy & Leadership: {strategy}/4 ("{strategy_label}")
- Data Readiness: {data}/4 ("{data_label}")
- Deployed Use Cases: {use_cases}/4 ("{use_cases_label}")
- AI Talent & Skills: {talent}/4 ("{talent_label}")
- AI Governance & Ethics: {governance}/4 ("{governance_label}")

Overall maturity score: {total}/20 → Tier: {tier}

Return a JSON object with this exact structure:

{{
  "tier": "{tier}",
  "tier_description": "<2-3 sentences characterizing what this maturity tier means for a company of this profile>",
  "sector_context": "<3-4 sentences: where companies of this size and type in this industry typically sit on AI adoption, citing specific survey data or benchmarks where available (e.g., 'McKinsey's 2024 Global AI Survey found that X% of financial services firms...'), and what separates laggards from leaders in this sector>",
  "dimension_assessments": {{
    "strategy":   {{"score": {strategy}, "label": "{strategy_label}", "benchmark": "<where this sector/size typically scores>", "gap": "<positive or negative gap vs benchmark, and what it means>"}},
    "data":       {{"score": {data},     "label": "{data_label}",     "benchmark": "<where this sector/size typically scores>", "gap": "<positive or negative gap vs benchmark, and what it means>"}},
    "use_cases":  {{"score": {use_cases},"label": "{use_cases_label}","benchmark": "<where this sector/size typically scores>", "gap": "<positive or negative gap vs benchmark, and what it means>"}},
    "talent":     {{"score": {talent},   "label": "{talent_label}",   "benchmark": "<where this sector/size typically scores>", "gap": "<positive or negative gap vs benchmark, and what it means>"}},
    "governance": {{"score": {governance},"label": "{governance_label}","benchmark": "<where this sector/size typically scores>", "gap": "<positive or negative gap vs benchmark, and what it means>"}}
  }},
  "strengths": ["<area where the organization is at or ahead of sector benchmark>", "<another strength if applicable>"],
  "priority_gaps": [
    {{"dimension": "<dimension name>", "why_it_matters": "<1-2 sentences on business impact of this gap>", "action": "<specific first step to close the gap>"}},
    {{"dimension": "<dimension name>", "why_it_matters": "<1-2 sentences>", "action": "<specific first step>"}},
    {{"dimension": "<dimension name>", "why_it_matters": "<1-2 sentences>", "action": "<specific first step>"}}
  ],
  "sector_leaders_note": "<For large enterprises: 1-2 sentences on what publicly known AI leaders in this sector have done that illustrates the ceiling. For smaller organizations: note that named-company comparison is limited and rely on survey aggregates.>",
  "data_confidence": "<high|medium|low> — rate your confidence in the sector benchmark data for this specific industry/size combination, and briefly note why>"
}}"""


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass
    if not key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set.")
    return key


def score_to_tier(total: int) -> str:
    if total <= 8:
        return "Low Adoption"
    elif total <= 12:
        return "Medium Adoption"
    elif total <= 16:
        return "High Adoption"
    else:
        return "AI Native"


@st.cache_data(ttl=3600, show_spinner=False)
def generate_benchmark(
    industry: str,
    company_type: str,
    company_size: str,
    scores: dict[str, int],
    context: str = "",
) -> dict:
    """
    Generate an AI adoption benchmark report.

    scores: dict with keys strategy, data, use_cases, talent, governance (each 1–4)
    Returns structured dict for Streamlit rendering.
    """
    client = anthropic.Anthropic(api_key=_get_api_key())

    total = sum(scores.values())
    tier = score_to_tier(total)

    # Build label strings for each dimension
    labels = {
        dim: DIMENSIONS[dim][1][scores[dim] - 1]
        for dim in DIMENSIONS
    }

    prompt = BENCHMARK_PROMPT.format(
        industry=industry,
        company_type=company_type,
        company_size=company_size,
        context=context or "No additional context provided.",
        strategy=scores["strategy"],      strategy_label=labels["strategy"],
        data=scores["data"],              data_label=labels["data"],
        use_cases=scores["use_cases"],    use_cases_label=labels["use_cases"],
        talent=scores["talent"],          talent_label=labels["talent"],
        governance=scores["governance"],  governance_label=labels["governance"],
        total=total,
        tier=tier,
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    result["total_score"] = total
    result["scores"] = scores
    result["labels"] = labels
    return result
