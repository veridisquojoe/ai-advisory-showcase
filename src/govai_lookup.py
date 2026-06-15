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
  share_e1_half_e2_human                   — AI exposure (0–1), Eloundou et al. 2024 human scores
  share_e1_half_e2_human_percentile        — AI exposure percentile rank (0–1)
  ac_gw-sw-imp-raw_log-md-nlw_dens_age55_pct — adaptive capacity percentile, main paper spec
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


@st.cache_data(ttl=3600, show_spinner=False)
def _load_govai_data() -> pd.DataFrame | None:
    """Download and cache the GovAI/Manning-Aguirre occupation data."""
    try:
        resp = requests.get(_GOVAI_CSV_URL, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # Keep only the columns we need
        keep = [_DESC_COL, _EXPOSURE_COL, _EXPOSURE_PCT_COL, _AC_COL, _EMP_COL]
        missing = [c for c in keep if c not in df.columns]
        if missing:
            return None
        df = df[keep].dropna(subset=[_DESC_COL, _EXPOSURE_COL, _AC_COL])
        df[_DESC_COL] = df[_DESC_COL].str.strip()
        return df
    except Exception:
        return None


def lookup_occupation(role: str, industry: str = "") -> dict | None:
    """
    Fuzzy-match a free-text role + industry to the closest GovAI occupation.

    Returns a dict with:
      matched_occupation   — occupation title from the dataset
      ai_exposure          — 0–1 share of tasks exposed to AI
      ai_exposure_pct      — percentile rank among all occupations
      adaptive_capacity    — 0–1 adaptive capacity percentile (main spec)
      is_vulnerable        — True if high exposure AND low adaptive capacity
      employment           — BLS employment count
      match_score          — difflib similarity score (0–1)
    """
    df = _load_govai_data()
    if df is None:
        return None

    query = f"{role} {industry}".strip().lower()
    occupations = df[_DESC_COL].tolist()
    occ_lower = [o.lower() for o in occupations]

    # Get best match via difflib
    matches = difflib.get_close_matches(query, occ_lower, n=1, cutoff=0.0)
    if not matches:
        return None

    best_lower = matches[0]
    # Also check with individual role words for better coverage
    role_words = set(role.lower().split())
    scored = []
    for i, occ in enumerate(occ_lower):
        seq_score = difflib.SequenceMatcher(None, query, occ).ratio()
        word_overlap = len(role_words & set(occ.split())) / max(len(role_words), 1)
        combined = 0.6 * seq_score + 0.4 * word_overlap
        scored.append((combined, i))
    scored.sort(reverse=True)
    best_idx = scored[0][1]
    best_score = scored[0][0]

    row = df.iloc[best_idx]
    exposure = float(row[_EXPOSURE_COL])
    ac = float(row[_AC_COL])

    # Vulnerability = top quartile exposure AND bottom quartile adaptive capacity
    is_vulnerable = (exposure >= 0.5) and (ac <= 0.35)

    # Exposure percentile — may be NaN for some rows; compute from series if needed
    exp_pct_val = row.get(_EXPOSURE_PCT_COL, None)
    if pd.isna(exp_pct_val):
        exp_pct_val = (df[_EXPOSURE_COL] <= exposure).mean()
    exp_pct = float(exp_pct_val)

    return {
        "matched_occupation": str(row[_DESC_COL]),
        "ai_exposure": exposure,
        "ai_exposure_pct": exp_pct,
        "adaptive_capacity": ac,
        "is_vulnerable": is_vulnerable,
        "employment": int(row[_EMP_COL]) if not pd.isna(row[_EMP_COL]) else None,
        "match_score": best_score,
    }


def data_available() -> bool:
    """Return True if the GovAI dataset loaded successfully."""
    return _load_govai_data() is not None
