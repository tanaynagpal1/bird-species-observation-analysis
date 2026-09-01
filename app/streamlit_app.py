"""
Bird Species Observation Analysis - dashboard entry point.

This file does four things and nothing else:

  1. sets the page config (must be the very first Streamlit call)
  2. injects the theme CSS
  3. builds the sidebar - branding, the filters every page shares, the artwork
  4. hands control to the page the user picked

Each navigation item is a separate file in app/views/. They are listed in PAGES
below; a page appears in the sidebar as soon as its file exists, so the nav grows
as the project is built rather than breaking on a file that is not written yet.

Run locally:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import art
import data_access as da
import theme

APP_DIR = Path(__file__).resolve().parent

# ------------------------------------------------------------------ 1. config
st.set_page_config(
    page_title="Bird Species Observation Analysis",
    page_icon="🕊️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ 2. theme
st.markdown(theme.css(), unsafe_allow_html=True)

# ------------------------------------------------------------------ 3. sidebar
# Streamlit's automatic nav (position="sidebar") always renders in a fixed
# slot, above anything st.sidebar adds - no amount of code reordering moves
# it. To get Logo -> Nav -> Filters, we hide the automatic one
# (position="hidden") and draw our own with st.page_link, placed exactly
# where we want it. st.navigation still has to run so Streamlit knows the
# page set and gives us `nav`, the currently-selected Page.

# (file, title, material icon)  - order here is the order in the sidebar.
PAGES = [
    ("views/overview.py",    "Overview",           ":material/home:"),
    ("views/habitat.py",     "Habitat Comparison", ":material/forest:"),
    ("views/species.py",     "Species",            ":material/flutter_dash:"),
    ("views/where.py",       "Where",              ":material/map:"),
    ("views/timing.py",      "Timing",             ":material/schedule:"),
    ("views/environment.py", "Environment",        ":material/partly_cloudy_day:"),
    ("views/quality.py",     "Data Quality",       ":material/verified:"),
    ("views/report.py",      "Report",             ":material/description:"),
    ("views/conclusion.py",  "Conclusion",         ":material/lightbulb:"),
    ("views/ask_ai.py",      "Ask AI",             ":material/smart_toy:"),
    ("views/tryit.py",       "Try It Yourself",    ":material/science:"),
]

pages = [
    st.Page(path, title=title, icon=icon, default=(i == 0))
    for i, (path, title, icon) in enumerate(PAGES)
    if (APP_DIR / path).exists()
]

if not pages:
    st.error("No page files found in app/views/. Nothing to show yet.")
    st.stop()

nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown(art.sidebar_header(), unsafe_allow_html=True)

    for pg in pages:
        st.page_link(
            pg,
            label=pg.title,
            icon=pg.icon,
            disabled=(pg.url_path == nav.url_path),
        )

# --- shared filters -------------------------------------------------------
# Built once, here, before the page runs. Every page reads st.session_state
# ["filters"], so a park chosen on Overview is still chosen on Species.
sess = da.sessions()
all_parks = sorted(sess["park_name"].dropna().unique().tolist())
all_months = ["May", "June", "July"]

with st.sidebar:
    st.markdown("###### Filters")

    shared_only = st.toggle(
        "Shared parks only",
        value=False,
        help="Guardrail G2. Restricts to the 4 parks that were surveyed in BOTH "
             "habitats - the only fair basis for a forest-vs-grassland comparison.",
    )

    habitat = st.radio(
        "Habitat",
        ["Both", "Forest", "Grassland"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # Left empty on purpose - empty means "everything", which keeps the sidebar
    # short instead of showing eleven park chips before the user has chosen
    # anything. apply_filters() treats an empty list as no filter.
    parks = st.multiselect("Parks", options=all_parks, placeholder="All 11 parks")
    months = st.multiselect("Months", options=all_months, placeholder="May - July")

    st.markdown(art.sidebar_scene(), unsafe_allow_html=True)

st.session_state["filters"] = {
    "shared_only": shared_only,
    "habitat": habitat,
    "parks": parks or all_parks,
    "months": months or all_months,
    "n_parks_total": len(all_parks),
}

# ------------------------------------------------------------------ 4. run
nav.run()