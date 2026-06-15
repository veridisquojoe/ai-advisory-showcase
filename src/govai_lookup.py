"""
govai_lookup.py
---------------
Fetches and caches the Manning & Aguirre (2025) occupation-level AI exposure
and adaptive capacity index from the public replication repository.

Data source:
  t6aguirre/adaptive-capacity-index (MIT License)
  https://github.com/t6aguirre/adaptive-capacity-index

Key columns used:
  description                              — occupation title (O*NET / SIPP)
  share_e1_half_e2_human                   — AI exposure (0–1), Eloundou et al. 2024
  share_e1_half_e2_human_percentile        — AI exposure percentile rank (0–1)
  ac_gw-sw-imp-raw_log-md-nlw_dens_age55_pct — adaptive capacity percentile, main spec
  total_emp                                — employment (BLS OEWS, count)

Paper citation:
  Sam J. Manning and Tomás Aguirre, "How Adaptable Are American Workers to
  AI-Induced Job Displacement?" NBER Working Paper 34705 (2026).
  https://doi.org/10.3386/w34705
"""

import io
import difflib
import streamlit as st
import pandas as pd
import requests

_GOVAI_CSV_URL = (
    "https://raw.githubusercontent.com/t6aguirre/adaptive-capacity-index"
    "/main/data/final/adaptive_capacity_results.csv"
)

# Main adaptive capacity column (paper's primary specification)
_AC_COL = "ac_gw-sw-imp-raw_log-md-nlw_dens_age55_pct"
_EXPOSURE_COL = "share_e1_half_e2_human"
_EXPOSURE_PCT_COL = "share_e1_half_e2_human_percentile"
_DESC_COL = "description"
_EMP_COL = "total_emp"

# ── Industry group definitions ─────────────────────────────────────────────────
# Keywords matched against lowercase occupation titles.
# Order matters: first matching group wins, so put more specific groups first.

INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "Architecture & Engineering": [
        "engineer", "architect", "drafter", "surveyor", "technician",
        "civil eng", "mechanical eng", "electrical eng", "aerospace",
    ],
    "Healthcare & Medical": [
        "nurse", "physician", "surgeon", "therapist", "dental",
        "pharmacy", "radiolog", "dietitian", "optometrist", "chiropractor",
        "anesthesi", "patholog", "veterinar", "paramedic", "medical",
        "health technolog", "health care", "healthcare",
    ],
    "Technology & IT": [
        "software", "computer", "information system", "network", "database",
        "data scientist", "cybersecurity", "web developer", "devops",
        "cloud", "developer", "programmer",
    ],
    "Finance, Insurance & Real Estate": [
        "financial", "accountant", "auditor", "budget analyst", "loan",
        "insurance", "investment", "actuary", "tax", "credit", "real estate",
        "mortgage", "underwriter", "securities", "portfolio",
    ],
    "Legal": [
        "lawyer", "attorney", "paralegal", "judge", "legal",
        "court", "arbitrat",
    ],
    "Education & Library": [
        "teacher", "instructor", "professor", "librarian",
        "principal", "curriculum", "postsecondary", "special education",
    ],
    "Arts, Design & Media": [
        "writer", "artist", "designer", "journalist", "photographer",
        "musician", "actor", "editor", "graphic", "animator", "broadcast",
        "public relation", "interpreter", "translator",
    ],
    "Science & Research": [
        "scientist", "researcher", "biologist", "chemist", "physicist",
        "geologist", "astronomer", "ecologist", "epidemiolog", "statistician",
        "social scientist", "economist", "psychologist",
    ],
    "Social Services & Community": [
        "social worker", "counselor", "community service", "clergy",
        "probation", "substance abuse", "mental health", "rehabilitation",
        "social and community",
    ],
    "Sales & Marketing": [
        "sales representative", "sales agent", "marketing", "advertising",
        "buyer", "merchandis", "promotions", "market research",
    ],
    "Administrative & Office Support": [
        "clerk", "secretary", "administrative assistant", "receptionist",
        "data entry", "bookkeeper", "payroll", "postal", "dispatcher",
        "office support", "customer service",
    ],
    "Food, Hospitality & Tourism": [
        "chef", "cook", "food", "hotel", "restaurant", "hospitality",
        "barista", "bartender", "waiter", "server", "baker", "dining",
    ],
    "Construction & Trades": [
        "electrician", "plumber", "carpenter", "construction", "mason",
        "roofer", "welder", "ironwork", "painter and", "hvac", "elevator",
        "boilermaker", "brickmason",
    ],
    "Transportation & Logistics": [
        "driver", "pilot", "air traffic", "logistics", "truck",
        "bus driver", "transit", "flight", "sailor", "ship", "rail",
    ],
    "Manufacturing & Production": [
        "production", "assembler", "manufacturing", "machinist",
        "quality control", "textile", "semiconductor", "plant operator",
    ],
    "Building & Grounds Maintenance": [
        "janitor", "cleaner", "groundskeeper", "landscap", "maid",
        "housekeeper", "pest control", "tree trimm", "building cleaning",
    ],
    "Personal Care & Services": [
        "barber", "hairdresser", "childcare", "personal care",
        "fitness trainer", "massage", "cosmetolog", "esthetician",
        "childcare worker",
    ],
    "Agriculture & Natural Resources": [
        "farmer", "agricultural", "fishery", "forestry", "logging",
        "mining", "farm worker", "crop", "livestock",
    ],
    "Government & Public Safety": [
        "police", "firefighter", "correctional", "security guard",
        "emergency management", "border patrol", "detective",
        "protective service",
    ],
    "Management & Executive": [
        "manager", "director", "executive", "chief", "president",
        "officer", "administrator", "superintendent", "commissioner",
        "operations manager",
    ],
}

# Default hourly rates by industry group (BLS-informed midpoint estimates)
INDUSTRY_RATE_DEFAULTS: dict[str, int] = {
    "Management & Executive": 90,
    "Technology & IT": 110,
    "Finance, Insurance & Real Estate": 80,
    "Healthcare & Medical": 80,
    "Education & Library": 55,
    "Legal": 100,
    "Sales & Marketing": 65,
    "Administrative & Office Support": 45,
    "Construction & Trades": 65,
    "Transportation & Logistics": 55,
    "Food, Hospitality & Tourism": 35,
    "Arts, Design & Media": 65,
    "Science & Research": 85,
    "Social Services & Community": 55,
    "Manufacturing & Production": 55,
    "Building & Grounds Maintenance": 40,
    "Personal Care & Services": 40,
    "Agriculture & Natural Resources": 40,
    "Government & Public Safety": 70,
    "Architecture & Engineering": 90,
    "Other": 65,
}


def assign_industry_group(title: str) -> str:
    """Keyword-classify an occupation title into a plain-language industry group."""
    t = title.lower()
    for group, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return group
    return "Other"


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _load_govai_data() -> pd.DataFrame | None:
    """Download and cache the GovAI/Manning-Aguirre occupation data."""
    try:
        resp = requests.get(_GOVAI_CSV_URL, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        keep = [_DESC_COL, _EXPOSURE_COL, _EXPOSURE_PCT_COL, _AC_COL, _EMP_COL]
        missing = [c for c in keep if c not in df.columns]
        if missing:
            return None
        df = df[keep].dropna(subset=[_DESC_COL, _EXPOSURE_COL, _AC_COL])
        df[_DESC_COL] = df[_DESC_COL].str.strip()
        return df
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_industry_occupation_map() -> dict[str, list[str]]:
    """
    Return {industry_group: [sorted occupation titles]} for all 356 occupations.
    Returns empty dict if data is unavailable.
    """
    df = _load_govai_data()
    if df is None:
        return {}
    result: dict[str, list[str]] = {}
    for title in df[_DESC_COL].tolist():
        group = assign_industry_group(title)
        result.setdefault(group, []).append(title)
    for group in result:
        result[group] = sorted(result[group])
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def get_scatter_data() -> pd.DataFrame | None:
    """
    Return enriched DataFrame for the vulnerability scatter chart.
    Adds industry_group and display-ready percentage columns.
    """
    df = _load_govai_data()
    if df is None:
        return None
    out = df.copy()
    out["industry_group"] = out[_DESC_COL].apply(assign_industry_group)
    out["ai_exposure_pct"] = (out[_EXPOSURE_COL] * 100).round(1)
    out["adaptive_capacity_pct"] = (out[_AC_COL] * 100).round(1)
    out["employment_fmt"] = out[_EMP_COL].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
    )
    return out


# ── Fuzzy matching ────────────────────────────────────────────────────────────

def _stem(word: str) -> str:
    """Light stemmer: strip common English suffixes so janitor ~ janitors."""
    for suffix in ("ers", "ians", "ists", "ors", "ees", "ing", "tion", "tions",
                   "er", "or", "ian", "ist", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: len(word) - len(suffix)]
    return word


def _score_match(query_tokens: list[str], occ: str) -> float:
    """
    Score how well query_tokens match an occupation string.

    Three components (all 0–1):
      seq (30%):    SequenceMatcher ratio, shorter string as needle
      prefix (35%): fraction of query tokens that are a prefix of any occ word
      stem (35%):   fraction of stemmed query tokens matching stemmed occ words
    """
    occ_words = occ.split()
    occ_stems = [_stem(w) for w in occ_words]

    prefix_hits = sum(
        1 for qt in query_tokens
        if any(ow.startswith(qt) or qt.startswith(ow) for ow in occ_words)
    )
    prefix_score = prefix_hits / max(len(query_tokens), 1)

    q_stems = [_stem(t) for t in query_tokens]
    stem_hits = sum(
        1 for qs in q_stems
        if qs in occ_stems or any(os.startswith(qs) for os in occ_stems)
    )
    stem_score = stem_hits / max(len(q_stems), 1)

    query_str = " ".join(query_tokens)
    if len(query_str) <= len(occ):
        seq = difflib.SequenceMatcher(None, query_str, occ).ratio()
    else:
        seq = difflib.SequenceMatcher(None, occ, query_str).ratio()

    return 0.3 * seq + 0.35 * prefix_score + 0.35 * stem_score


def _build_result(row: pd.Series, df: pd.DataFrame, score: float) -> dict:
    exposure = float(row[_EXPOSURE_COL])
    ac = float(row[_AC_COL])
    is_vulnerable = (exposure >= 0.5) and (ac <= 0.35)
    exp_pct_val = row.get(_EXPOSURE_PCT_COL, None)
    if pd.isna(exp_pct_val):
        exp_pct_val = (df[_EXPOSURE_COL] <= exposure).mean()
    return {
        "matched_occupation": str(row[_DESC_COL]),
        "ai_exposure": exposure,
        "ai_exposure_pct": float(exp_pct_val),
        "adaptive_capacity": ac,
        "is_vulnerable": is_vulnerable,
        "employment": int(row[_EMP_COL]) if pd.notna(row[_EMP_COL]) else None,
        "match_score": score,
    }


def lookup_by_title(title: str) -> dict | None:
    """
    Direct lookup by exact occupation title (case-insensitive).
    Falls back to fuzzy match if no exact match is found.
    """
    df = _load_govai_data()
    if df is None:
        return None
    mask = df[_DESC_COL].str.lower() == title.lower().strip()
    if mask.any():
        row = df[mask].iloc[0]
        return _build_result(row, df, 1.0)
    return lookup_occupation(title)


def lookup_occupation(role: str, industry: str = "") -> dict | None:
    """
    Fuzzy-match a free-text role + industry to the closest GovAI occupation.

    Returns a dict with:
      matched_occupation   — occupation title from the dataset
      ai_exposure          — 0–1 share of tasks exposed to AI
      ai_exposure_pct      — percentile rank among all occupations (0–1)
      adaptive_capacity    — 0–1 adaptive capacity percentile (main spec)
      is_vulnerable        — True if high exposure AND low adaptive capacity
      employment           — BLS employment count
      match_score          — combined similarity score (0–1)
    """
    df = _load_govai_data()
    if df is None:
        return None

    STOP = {"and", "or", "the", "a", "an", "of", "in", "at", "for", "to", "with"}
    role_tokens = [t for t in role.lower().split() if t not in STOP]
    industry_tokens = [t for t in industry.lower().split() if t not in STOP]
    query_tokens = role_tokens + [t for t in industry_tokens if t not in role_tokens]

    if not query_tokens:
        return None

    occ_lower = [o.lower() for o in df[_DESC_COL].tolist()]
    scored = [
        (_score_match(query_tokens, occ), i)
        for i, occ in enumerate(occ_lower)
    ]
    scored.sort(reverse=True)
    best_idx = scored[0][1]
    best_score = scored[0][0]

    row = df.iloc[best_idx]
    return _build_result(row, df, best_score)


def data_available() -> bool:
    """Return True if the GovAI dataset loaded successfully."""
    return _load_govai_data() is not None
