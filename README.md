# AI Task Advisor

An interactive AI advisory tool that analyzes any role, classifies its tasks by the best AI method, and estimates ROI — powered by Claude and grounded in the PMI/CPMAI framework.

**Live demo:** *(add Streamlit Cloud link)*

---

## What it does

Enter a job title, industry, and hourly rate. The tool:

1. **Enumerates the role's key tasks** — realistic, week-to-week activities
2. **Classifies each task** by AI method using the PMI CPMAI taxonomy:
   - 🔵 **LLM** — language generation, summarization, Q&A, drafting
   - 🟠 **Traditional ML** — prediction, classification, anomaly detection
   - 🟢 **Automation** — rule-based, deterministic, scripted workflows
   - ⚪ **Human Only** — relationship, negotiation, ethical judgment
3. **Recommends tools** available today for each task
4. **Estimates time saved** and annual dollar value at the role's hourly rate
5. **Prioritizes implementation** — Quick Wins first, then Medium and Long Term

Pre-built examples: **Real Estate Agent** and **API Developer**.

---

## Why this matters for organizations

Most AI strategy engagements fail not because the technology doesn't work, but because organizations try to apply AI to the wrong tasks. A structured task assessment surfaces:

- Which tasks are genuinely suited for LLMs vs. traditional ML vs. simple automation
- Where the highest ROI opportunities are (Quick Wins)
- What implementation complexity to expect
- Which tasks should stay human — and why

This tool makes that conversation concrete and data-driven from the first client meeting.

---

## Setup

```bash
git clone https://github.com/beatzbyJWE/ai-advisory-showcase.git
cd ai-advisory-showcase
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
streamlit run app.py
```

---

## Methodology

Built on the **PMI Certified Professional in Managing AI (CPMAI)** framework, which classifies AI tasks by:

- **Perception** (sensing/reading) → Traditional ML or LLM
- **Language** (reading/writing/summarizing) → LLM
- **Judgment** (deciding from patterns) → Traditional ML
- **Rule execution** (deterministic steps) → Automation
- **Social** (relationships, trust, accountability) → Human Only

The CPMAI credential (held by the author) is PMI's AI management certification for practitioners leading AI initiatives in organizations.

---

## Author

**Joseph Eldredge** | PMP, CPMAI  
[eldredgemgmtconsulting.com](https://eldredgemgmtconsulting.com) · AI advisory and program management for SMBs and public sector
