"""
One place where the dashboard touches data.

Every page imports from here. Nothing else in app/ opens a CSV or recomputes a
statistic. Two reasons:

1. Caching. Streamlit re-runs the whole script on every widget click. Without
   @st.cache_data we would re-read 7 MB and re-run 13 analyses on every filter
   change. With it, the work happens once per session.

2. One number, one source. Every headline figure on the dashboard comes from
   analysis.py - the same file the notebooks and the PDF report use. Nothing is
   typed in by hand, so a figure can never drift out of sync with the analysis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------- paths
APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
SRC_DIR = ROOT / "src"
PROCESSED = ROOT / "data" / "processed"
REFERENCE = ROOT / "data" / "reference"

# src/ is not a package, so make it importable before importing analysis.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# --------------------------------------------------------------- tables
@st.cache_data(show_spinner=False)
def birds() -> pd.DataFrame:
    """15,372 cleaned observations with the calculated fields attached."""
    return pd.read_csv(PROCESSED / "birds_features.csv", low_memory=False)


@st.cache_data(show_spinner=False)
def sessions() -> pd.DataFrame:
    """1,408 survey sessions. This is the unit of survey effort (guardrail G1)."""
    return pd.read_csv(PROCESSED / "sessions.csv")


@st.cache_data(show_spinner=False)
def species() -> pd.DataFrame:
    """114 species scored for habitat preference, shared parks only."""
    return pd.read_csv(PROCESSED / "species_profile.csv")


@st.cache_data(show_spinner=False)
def park_coordinates() -> pd.DataFrame:
    """11 parks with latitude / longitude and a precision column."""
    return pd.read_csv(REFERENCE / "park_coordinates.csv")


@st.cache_data(show_spinner=False)
def results() -> dict:
    """
    Every verified statistic (Q1-Q12), computed by src/analysis.py.

    Takes about 1.5 seconds the first time, then comes from cache. The import is
    inside the function so that a broken analysis.py surfaces as a clear error on
    the page that needs it, rather than a blank app at start-up.
    """
    import analysis

    return analysis.run_all(ROOT)


# --------------------------------------------------------------- filters
def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """
    Apply the sidebar filters to any table that has habitat / park / month.

    Deliberately tolerant: if a table does not carry one of these columns, that
    filter is skipped rather than raising. Keeps page code free of guard clauses.
    """
    out = df

    if f.get("shared_only") and "is_shared_park" in out.columns:
        out = out[out["is_shared_park"]]

    if f.get("habitat") and f["habitat"] != "Both" and "habitat" in out.columns:
        out = out[out["habitat"] == f["habitat"]]

    parks = f.get("parks") or []
    if parks and "park_name" in out.columns:
        out = out[out["park_name"].isin(parks)]

    months = f.get("months") or []
    if months and "month_name" in out.columns:
        out = out[out["month_name"].isin(months)]

    return out


def filter_summary(f: dict, n_parks_total: int) -> str:
    """One short line describing what the user is currently looking at."""
    bits = []
    bits.append("Both habitats" if f.get("habitat") == "Both" else f.get("habitat", "Both"))

    parks = f.get("parks") or []
    if f.get("shared_only"):
        bits.append("shared parks only")
    elif len(parks) == n_parks_total:
        bits.append(f"all {n_parks_total} parks")
    else:
        bits.append(f"{len(parks)} of {n_parks_total} parks")

    months = f.get("months") or []
    bits.append("May-July" if len(months) == 3 else ", ".join(months) if months else "no months")

    return "  ·  ".join(bits)