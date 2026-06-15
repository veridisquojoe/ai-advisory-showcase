"""
classifier.py
-------------
Claude-powered task classifier using the PMI/CPMAI AI task taxonomy.

For a given role and workflow description, Claude:
  1. Enumerates the role's key recurring tasks
  2. Classifies each by the best AI method (LLM / Traditional ML / Automation / Human)
  3. Recommends specific tools
  4. Estimates weekly hours spent and % reducible by AI
  5. Returns structured JSON for the Streamlit UI to render
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

# ── PMI/CPMAI task taxonomy ───────────────────────────────────────────────────
TAXONOMY = """
PMI CPMAI AI Task Classification Taxonomy:

• LLM (Large Language Model)
  Best for: language generation, summarization, drafting, Q&A, document analysis,
  client communication, meeting notes, research synthesis, contract review.
  Signals: task involves reading/writing natural language, judgment on unstructured text,
  or generating human-readable output.

• Traditional ML
  Best for: prediction from structured data, pattern recognition, anomaly detection,
  classification of labeled datasets, forecasting, scoring/ranking.
  Signals: task has historical data with outcomes, clear input features, measurable accuracy.

• Automation (RPA / Scripting)
  Best for: deterministic, rule-based, repetitive tasks with no ambiguity.
  Signals: task follows the same steps every time, no judgment required, triggers on
  a clear condition, involves moving data between systems.

• Human Only
  Best for: relationship management, negotiation, ethical judgment, creative strategy,
  novel problem-solving, high-stakes decisions requiring accountability.
  Signals: task requires empathy, trust, legal accountability, or genuine creativity
  that cannot be verified by an external standard.
"""

SYSTEM_PROMPT = f"""You are an AI strategy consultant applying the PMI/CPMAI framework to help
organizations identify which tasks are best suited for AI augmentation and which should remain human.

{TAXONOMY}

When analyzing a role, be specific and practical. Focus on tasks that are genuinely performed
week-to-week, not aspirational activities. For each task, think carefully about:
- Whether the task is language-based (favors LLM), data-pattern-based (favors ML),
  rule-based (favors Automation), or relationship/judgment-based (Human Only)
- Realistic time estimates based on the role
- Tools that are commercially available today, not theoretical

Always respond with valid JSON only. No markdown, no explanation outside the JSON structure."""

CLASSIFICATION_PROMPT = """Analyze the following role and return a JSON object with this exact structure:

{{
  "role": "<role name>",
  "summary": "<2-3 sentence overview of where AI creates the most value in this role>",
  "tasks": [
    {{
      "task": "<task name, max 8 words>",
      "description": "<what this task involves, 1-2 sentences>",
      "category": "<LLM | Traditional ML | Automation | Human Only>",
      "rationale": "<1 sentence: why this category fits per the CPMAI taxonomy>",
      "tools": ["<tool 1>", "<tool 2>", "<tool 3>"],
      "weekly_hours": <estimated weekly hours spent on this task, integer>,
      "reducible_pct": <percentage of that time AI can eliminate or reduce, 0-90, integer>,
      "complexity": "<Low | Medium | High>",
      "priority": "<Quick Win | Medium Term | Long Term>"
    }}
  ],
  "implementation_notes": "<2-3 sentences on sequencing: what to tackle first and why>"
}}

Role: {role}
Industry context: {industry}
Additional context: {context}

Return 8-12 tasks that represent the most time-consuming or impactful parts of this role.
Ensure a realistic mix of categories — not everything is suitable for LLMs."""


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


def classify_role(role: str, industry: str = "", context: str = "", hourly_rate: float = 75.0) -> dict:
    """
    Run the full classification pipeline for a given role.
    Returns a dict with tasks, ROI summary, and chart-ready data.
    """
    client = anthropic.Anthropic(api_key=_get_api_key())

    prompt = CLASSIFICATION_PROMPT.format(
        role=role,
        industry=industry or "General",
        context=context or "No additional context provided.",
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
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

    data = json.loads(raw)

    # Compute ROI fields
    for task in data.get("tasks", []):
        weekly_hours = task.get("weekly_hours", 0)
        reducible_pct = task.get("reducible_pct", 0)
        hours_saved = round(weekly_hours * reducible_pct / 100, 1)
        task["hours_saved_weekly"] = hours_saved
        task["annual_savings"] = round(hours_saved * 52 * hourly_rate)

    tasks = data.get("tasks", [])
    total_weekly_hours = sum(t.get("weekly_hours", 0) for t in tasks)
    total_hours_saved = sum(t.get("hours_saved_weekly", 0) for t in tasks)
    total_annual_savings = sum(t.get("annual_savings", 0) for t in tasks)

    data["roi_summary"] = {
        "hourly_rate": hourly_rate,
        "total_weekly_hours_analyzed": total_weekly_hours,
        "total_weekly_hours_saved": round(total_hours_saved, 1),
        "total_annual_savings": total_annual_savings,
        "roi_pct": round((total_hours_saved / total_weekly_hours * 100) if total_weekly_hours else 0, 1),
    }

    return data
