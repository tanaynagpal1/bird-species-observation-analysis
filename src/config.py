"""
Central configuration for the bird species observation pipeline.

Everything that another module might need to know about *where things live*
or *what the data should look like* is defined here, once.

Why the expected counts live in this file
-----------------------------------------
Each pipeline stage asserts against these numbers. If the source workbooks
are ever replaced or re-exported, the pipeline fails loudly at the exact
stage where the change entered - instead of silently producing a different
headline figure six steps later.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------- paths
# ROOT resolves to the project folder (the parent of src/), regardless of
# where the script is run from. Using pathlib rather than string joins
# keeps this correct on Windows and on the Linux deployment host.
ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REFERENCE_DIR = ROOT / "data" / "reference"
SQL_DIR = ROOT / "sql"
DOCS_DIR = ROOT / "docs"

FOREST_XLSX = RAW_DIR / "bird_monitoring_data_forest.xlsx"
GRASSLAND_XLSX = RAW_DIR / "bird_monitoring_data_grassland.xlsx"

CLEAN_CSV = PROCESSED_DIR / "birds_clean.csv"
DB_PATH = PROCESSED_DIR / "birds.db"
PARK_COORDS_CSV = REFERENCE_DIR / "park_coordinates.csv"
CLEANING_LOG = DOCS_DIR / "cleaning_log.md"

# All file reads and writes must pass this explicitly. Python on Windows
# defaults to cp1252, which corrupts any non-ASCII character we write into
# the cleaning log or the report. See blueprint section 8, rule E1.
ENCODING = "utf-8"

# --------------------------------------------------------------- expected shape
# Asserted by ingest.py against the raw workbooks.
EXPECTED_RAW_ROWS = {"Forest": 8546, "Grassland": 8531}

# Asserted by clean.py.
EXPECTED_GRASSLAND_DUPLICATES = 1705
EXPECTED_CLEAN_ROWS = 15372  # 8546 forest + 6826 grassland after deduplication

# Asserted by features.py.
EXPECTED_SESSIONS = 1408

# --------------------------------------------------------------- domain constants
# A survey session is one observer at one plot on one date for one visit.
# It is the unit of survey effort, and guardrails G1 and G3 both depend on it:
# every rate we report is "per session", never a raw total.
SESSION_KEYS = ["Plot_Name", "Date", "Visit"]

# The species key. Chosen over AcceptedTSN, TaxonCode and AOU_Code because it
# is the only species identifier with zero missing values (decision #8).
SPECIES_KEY = "Scientific_Name"

# Guardrail G2. Habitat comparisons are only valid in parks where BOTH
# habitats were surveyed. Pooling all 11 parks produces a statistically
# significant but false result - see blueprint section 3.
SHARED_PARKS = ["ANTI", "HAFE", "MANA", "MONO"]

# The 11 National Park Service units represented in this dataset.
PARK_NAMES = {
    "ANTI": "Antietam National Battlefield",
    "CATO": "Catoctin Mountain Park",
    "CHOH": "Chesapeake & Ohio Canal National Historical Park",
    "GWMP": "George Washington Memorial Parkway",
    "HAFE": "Harpers Ferry National Historical Park",
    "MANA": "Manassas National Battlefield Park",
    "MONO": "Monocacy National Battlefield",
    "NACE": "National Capital East Parks",
    "PRWI": "Prince William Forest Park",
    "ROCR": "Rock Creek Park",
    "WOTR": "Wolf Trap National Park for the Performing Arts",
}

# --------------------------------------------------------------- theme
# "Nature / illustrated" - locked. Validated for colour-vision deficiency and
# contrast against the cream surface. Do not substitute colours without
# re-running the validation described in blueprint section 4.
THEME = {
    "forest": "#12805c",      # deep forest green - the Forest series
    "grassland": "#b07d0a",   # dark gold - the Grassland series
    "at_risk": "#c0392b",     # reserved status colour, never a series
    "page": "#f6f4ec",        # cream
    "card": "#ffffff",
    "border": "#e4e1d5",
    "grid": "#e8e5da",
    "ink": "#1a2620",
    "ink2": "#5c6a61",
    "muted": "#8a968d",
    "sidebar_top": "#16311f",
    "sidebar_bottom": "#1d4029",
    "kpi_top": "#1b3a25",
    "kpi_bottom": "#245030",
    "nav_active": "#2b6b45",
}
