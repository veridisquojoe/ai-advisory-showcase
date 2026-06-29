"""
exec_brief.py
-------------
Claude-powered AI investment brief for executive audiences (CEO / CFO).

Given an industry, company type, and size profile, Claude identifies where
AI investment would yield the highest ROI — framed as strategic opportunities
rather than a task-level breakdown.
"""

import os
import json
import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-6"

AVAILABLE_MODELS = {
    "Claude Sonnet (faster, recommended)": "claude-sonnet-4-6",
    "Claude Opus (more thorough, slower)": "claude-opus-4-6",
}

SYSTEM_PROMPT = """You are a senior AI strategy advisor preparing investment briefs for CEOs and CFOs.
Your job is to identify where AI would generate the highest business return for a specific company profile.

Guiding principles:
- Be specific to the company type, size, and industry — not generic.
- Focus on ROI, competitive advantage, and risk reduction — not technology novelty.
- Prioritize initiatives that are achievable within a realistic budget and timeline for the company's scale.
- Distinguish between quick wins (low investment, near-term return) and strategic bets (higher investment, longer payoff).
- Call out the most common mistake companies make when investing in AI in this context.
- Frame everything from a business outcome lens, not a technology lens.

Always respond with valid JSON only. No markdown, no explanation outside the JSON structure."""

BRIEF_PROMPT = """Prepare an AI investment brief for the following company profile:

Industry: {industry}
Company type: {company_type}
Company size: {company_size}
Additional context: {context}

Return a JSON object with this exact structure:

{{
  "headline": "<one punchy sentence capturing the single biggest AI opportunity for this profile>",
  "summary": "<3-4 sentences: the AI investment landscape for this type of company, what separates companies that see real ROI from those that don't, and the core strategic posture to take>",
  "investment_areas": [
    {{
      "area": "<investment area name, e.g. 'Customer Communication Automation'>",
      "opportunity": "<1-2 sentences: the specific business opportunity or pain point this addresses>",
      "rationale": "<1 sentence: why this is the right fit for this company size and type>",
      "priority": "<Quick Win | Medium Term | Long Term>",
      "time_horizon": "<e.g. '1–3 months' | '3–12 months' | '12–24 months'>",
      "est_impact": "<concise description of the expected business impact, e.g. '20-30% reduction in X' or '$Y savings per year at this scale'>",
      "tools": ["<specific tool or platform>", "<specific tool or platform>"],
      "investment_level": "<Low (<$10K) | Medium ($10K–$100K) | High (>$100K)>"
    }}
  ],
  "key_risks": [
    "<risk 1: most common failure mode for AI investment at this company type/size>",
    "<risk 2: a data, talent, or change-management risk specific to this profile>",
    "<risk 3: a regulatory, vendor, or competitive risk worth flagging>"
  ],
  "recommended_first_step": "<1-2 sentences: the single most important thing this executive team should do in the next 30 days to start generating AI ROI>",
  "common_mistake": "<1-2 sentences: the most common mistake companies like this make when investing in AI — and what to do instead>"
}}

Return 4–6 investment areas covering a range of priorities (at least one Quick Win, at least one Medium Term, at least one Long Term).
Be specific to this exact profile — a 20-person professional services firm and a 500-person manufacturer require very different advice."""


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


@st.cache_data(ttl=3600, show_spinner=False)
def generate_exec_brief(
    industry: str,
    company_type: str,
    company_size: str,
    context: str = "",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Generate an executive AI investment brief for the given company profile.
    Returns a structured dict ready for the Streamlit UI to render.
    """
    client = anthropic.Anthropic(api_key=_get_api_key())

    prompt = BRIEF_PROMPT.format(
        industry=industry,
        company_type=company_type,
        company_size=company_size,
        context=context or "No additional context provided.",
    )

    message = client.messages.create(
        model=model,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
