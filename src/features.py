r"""
Phase 3 - Calculated fields.

Takes the cleaned dataset and derives everything the analysis and dashboard
need. Nothing here changes an observation; it only adds columns that make
later steps possible or safe.

Four files come out of this stage:

  data/processed/birds_features.csv   row level - one row per sighting
  data/processed/sessions.csv         session level - one row per survey
  data/processed/species_profile.csv  species level - one row per species
  data/reference/park_coordinates.csv  park level - one row per park

Why four tables rather than one wide one
----------------------------------------
The project's guardrails are all expressed per SURVEY SESSION, not per
sighting. Storing "species seen in this session" on every row of that session
would repeat the same number ten times and invite someone to average it - which
would silently weight sessions by how many birds they recorded.

Keeping the session table separate makes the correct unit explicit: if a
metric is per session, it lives in sessions.csv and you cannot accidentally
compute it from the row table.

Run it:

    python src/features.py
"""
from __future__ import annotations

import pandas as pd

from config import (
    CLEAN_CSV,
    ENCODING,
    EXPECTED_CLEAN_ROWS,
    EXPECTED_SESSIONS,
    PARK_COORDS_CSV,
    PARK_NAMES,
    PROCESSED_DIR,
    REFERENCE_DIR,
    SHARED_PARKS,
)

FEATURES_CSV = PROCESSED_DIR / "birds_features.csv"
SESSIONS_CSV = PROCESSED_DIR / "sessions.csv"
SPECIES_CSV = PROCESSED_DIR / "species_profile.csv"

# Season start, used for day_of_season. The first survey date in the dataset.
SEASON_START = pd.Timestamp("2018-05-07")

# Approximate centre point of each National Park Service unit, from public NPS
# and USGS sources. These are unit centroids, not survey plot positions - the
# plot identifiers in this dataset are internal survey IDs with no public
# coordinate lookup, so plot-level mapping is not possible.
#
# Precision varies by park and that matters when reading the map. CHOH is a
# 184-mile linear canal park and NACE is a collection of scattered sites
# around Washington DC; a single point for either is a rough convenience, not
# a real location. Compact parks such as ANTI and MONO are accurate to within
# a kilometre or so.
PARK_COORDINATES = {
    "ANTI": (39.4676, -77.7411, "compact"),
    "CATO": (39.6338, -77.4491, "compact"),
    "CHOH": (39.0000, -77.2500, "very approximate - 184-mile linear park"),
    "GWMP": (38.8977, -77.0708, "approximate - linear parkway"),
    "HAFE": (39.3251, -77.7386, "compact"),
    "MANA": (38.8118, -77.5216, "compact"),
    "MONO": (39.3712, -77.3936, "compact"),
    "NACE": (38.8600, -76.9800, "very approximate - scattered sites"),
    "PRWI": (38.5843, -77.3405, "compact"),
    "ROCR": (38.9600, -77.0500, "approximate - linear park"),
    "WOTR": (38.9385, -77.2647, "compact"),
}


def _time_band(hour) -> str:
    """Group the survey start hour into three readable bands."""
    if pd.isna(hour):
        return "Unknown"
    if hour <= 6:
        return "Early (5-6am)"
    if hour <= 8:
        return "Mid (7-8am)"
    return "Late (9-10am)"


def add_row_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive the row-level columns."""
    df = df.copy()

    # --- identity and grouping ------------------------------------------
    df["Date"] = pd.to_datetime(df["Date"])

    # THE key derived field. One observer, one plot, one date, one visit.
    # Every rate metric in the project divides by a count of these.
    df["session_id"] = (
        df["Plot_Name"].astype(str)
        + "|" + df["Date"].dt.strftime("%Y-%m-%d")
        + "|V" + df["Visit"].astype(int).astype(str)
    )

    df["habitat"] = df["Location_Type"]
    df["park_name"] = df["Admin_Unit_Code"].map(PARK_NAMES)

    # Guardrail G2 filters on this. Habitat comparisons are only valid in
    # parks where BOTH habitats were surveyed.
    df["is_shared_park"] = df["Admin_Unit_Code"].isin(SHARED_PARKS)

    # --- time ------------------------------------------------------------
    df["year"] = df["Date"].dt.year
    df["quarter"] = df["Date"].dt.year.astype(str) + "-Q" + df["Date"].dt.quarter.astype(str)
    df["month"] = df["Date"].dt.to_period("M").astype(str)
    df["month_name"] = df["Date"].dt.strftime("%B")
    # Computed but deliberately never charted - weekly sample sizes are too
    # uneven and produce noise spikes (decision #12).
    df["week"] = df["Date"].dt.isocalendar().week.astype(int)
    df["day_of_season"] = (df["Date"] - SEASON_START).dt.days

    start = pd.to_datetime(df["Start_Time"].astype(str), format="mixed", errors="coerce")
    end = pd.to_datetime(df["End_Time"].astype(str), format="mixed", errors="coerce")
    df["start_hour"] = start.dt.hour
    df["time_band"] = df["start_hour"].map(_time_band)
    df["session_duration_min"] = (end - start).dt.total_seconds() / 60

    # --- boolean flags, as real booleans ---------------------------------
    # The source columns are already boolean, but going through a string
    # comparison makes this robust to how the CSV round-trips them.
    for out, src in (
        ("is_at_risk", "PIF_Watchlist_Status"),
        ("is_stewardship", "Regional_Stewardship_Status"),
        ("is_flyover", "Flyover_Observed"),
        ("in_first_three_min", "Initial_Three_Min_Cnt"),
    ):
        df[out] = df[src].astype(str).str.strip().str.lower().isin(["true", "1"])

    # --- binning for charts ----------------------------------------------
    # Raw scatter of 1,408 points is unreadable; bands make the pattern legible.
    df["temp_band"] = pd.cut(
        pd.to_numeric(df["Temperature"], errors="coerce"),
        bins=[-100, 15, 20, 25, 30, 100],
        labels=["<15C", "15-20C", "20-25C", "25-30C", ">30C"],
    ).astype(str)
    df["humidity_band"] = pd.cut(
        pd.to_numeric(df["Humidity"], errors="coerce"),
        bins=[-1, 40, 60, 80, 101],
        labels=["<40%", "40-60%", "60-80%", ">80%"],
    ).astype(str)

    return df


def build_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per survey session, with the metrics the guardrails require.

    This is the table almost every analysis should start from. A "rate" in
    this project means a column of this table averaged over sessions - never
    a count taken from the row-level data.
    """
    sessions = (
        df.groupby("session_id", as_index=False)
        .agg(
            Admin_Unit_Code=("Admin_Unit_Code", "first"),
            park_name=("park_name", "first"),
            habitat=("habitat", "first"),
            is_shared_park=("is_shared_park", "first"),
            Plot_Name=("Plot_Name", "first"),
            Site_Name=("Site_Name", "first"),
            Date=("Date", "first"),
            Visit=("Visit", "first"),
            Observer=("Observer", "first"),
            month=("month", "first"),
            month_name=("month_name", "first"),
            week=("week", "first"),
            day_of_season=("day_of_season", "first"),
            start_hour=("start_hour", "first"),
            time_band=("time_band", "first"),
            session_duration_min=("session_duration_min", "first"),
            Temperature=("Temperature", "first"),
            Humidity=("Humidity", "first"),
            temp_band=("temp_band", "first"),
            humidity_band=("humidity_band", "first"),
            Sky=("Sky", "first"),
            Wind=("Wind", "first"),
            Disturbance=("Disturbance", "first"),
            species_per_session=("Scientific_Name", "nunique"),
            sightings_per_session=("Scientific_Name", "size"),
            at_risk_sightings=("is_at_risk", "sum"),
            flyovers=("is_flyover", "sum"),
        )
    )
    sessions["pct_at_risk_per_session"] = (
        sessions["at_risk_sightings"] / sessions["sightings_per_session"] * 100
    ).round(2)
    sessions["has_at_risk"] = sessions["at_risk_sightings"] > 0
    return sessions


def build_species_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per species, with its habitat preference.

    Habitat preference is computed on the SHARED PARKS ONLY (guardrail G2).
    Using all parks would let a species look grassland-preferring simply
    because grassland was surveyed in parks where that species happens to be
    common - which is the same confound that invalidates the naive habitat
    comparison.
    """
    shared = df[df["is_shared_park"]]

    counts = (
        shared.groupby(["Scientific_Name", "habitat"]).size().unstack(fill_value=0)
    )
    for h in ("Forest", "Grassland"):
        if h not in counts.columns:
            counts[h] = 0

    profile = pd.DataFrame(
        {
            "Scientific_Name": counts.index,
            "forest_sightings": counts["Forest"].to_numpy(),
            "grassland_sightings": counts["Grassland"].to_numpy(),
        }
    )
    profile["total_sightings"] = (
        profile["forest_sightings"] + profile["grassland_sightings"]
    )
    profile["grassland_share_pct"] = (
        profile["grassland_sightings"] / profile["total_sightings"] * 100
    ).round(1)

    # A species needs enough sightings before "preference" means anything.
    # Below this threshold the share is dominated by chance.
    WELL_SAMPLED = 20
    profile["well_sampled"] = profile["total_sightings"] >= WELL_SAMPLED

    def classify(row):
        if not row["well_sampled"]:
            return "Insufficient data"
        if row["grassland_share_pct"] > 90:
            return "Grassland specialist"
        if row["grassland_share_pct"] < 10:
            return "Forest specialist"
        return "Generalist"

    profile["specialist_class"] = profile.apply(classify, axis=1)

    names = df.drop_duplicates("Scientific_Name").set_index("Scientific_Name")
    profile["Common_Name"] = profile["Scientific_Name"].map(names["Common_Name"])
    profile["is_at_risk"] = profile["Scientific_Name"].map(names["is_at_risk"])
    profile["AOU_Code"] = profile["Scientific_Name"].map(names["AOU_Code"])

    cols = [
        "Scientific_Name", "Common_Name", "AOU_Code", "is_at_risk",
        "forest_sightings", "grassland_sightings", "total_sightings",
        "grassland_share_pct", "well_sampled", "specialist_class",
    ]
    return profile[cols].sort_values("total_sightings", ascending=False)


def build_park_coordinates() -> pd.DataFrame:
    """
    Park centroid lookup for the map.

    The precision column is not decoration: a map that shows CHOH as a single
    dot is showing the midpoint of a 184-mile canal. The dashboard must
    surface that caveat rather than implying a survey happened at that point.
    """
    return pd.DataFrame(
        [
            {
                "Admin_Unit_Code": code,
                "park_name": PARK_NAMES[code],
                "latitude": lat,
                "longitude": lon,
                "precision": note,
            }
            for code, (lat, lon, note) in PARK_COORDINATES.items()
        ]
    )


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(CLEAN_CSV, encoding=ENCODING)
    if len(df) != EXPECTED_CLEAN_ROWS:
        raise AssertionError(
            f"Expected {EXPECTED_CLEAN_ROWS:,} rows in {CLEAN_CSV.name}, "
            f"got {len(df):,}. Re-run src/clean.py."
        )

    df = add_row_features(df)
    sessions = build_sessions(df)
    species = build_species_profile(df)
    parks = build_park_coordinates()

    if len(sessions) != EXPECTED_SESSIONS:
        raise AssertionError(
            f"Expected {EXPECTED_SESSIONS:,} sessions, got {len(sessions):,}. "
            "The session key (plot + date + visit) may no longer be unique."
        )

    # Every park in the data must have coordinates, or the map silently drops it.
    missing = set(df["Admin_Unit_Code"].unique()) - set(parks["Admin_Unit_Code"])
    if missing:
        raise AssertionError(f"No coordinates for parks: {sorted(missing)}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(FEATURES_CSV, index=False, encoding=ENCODING)
    sessions.to_csv(SESSIONS_CSV, index=False, encoding=ENCODING)
    species.to_csv(SPECIES_CSV, index=False, encoding=ENCODING)
    parks.to_csv(PARK_COORDS_CSV, index=False, encoding=ENCODING)

    return df, sessions, species, parks


if __name__ == "__main__":
    df, sessions, species, parks = build()

    print("\nPhase 3 - Calculated fields")
    print("=" * 62)
    print(f"  Rows                  : {len(df):,}  ({df.shape[1]} columns)")
    print(f"  Sessions              : {len(sessions):,}  ({sessions.shape[1]} columns)")
    print(f"  Species profiled      : {len(species):,}")
    print(f"  Parks with coordinates: {len(parks)}")

    print("\n  Session length (minutes), by habitat:")
    for hab, grp in sessions.groupby("habitat"):
        print(f"    {hab:<10} median {grp.session_duration_min.median():.1f}"
              f"   n={len(grp):,}")

    print("\n  Species per session, by habitat (all parks - descriptive only):")
    for hab, grp in sessions.groupby("habitat"):
        print(f"    {hab:<10} mean {grp.species_per_session.mean():.2f}")

    print("\n  Habitat specialists (shared parks, >=20 sightings):")
    for cls, n in species.specialist_class.value_counts().items():
        print(f"    {cls:<22} {n:>3}")

    print(f"\n  Written: {FEATURES_CSV.name}, {SESSIONS_CSV.name}, "
          f"{SPECIES_CSV.name}, {PARK_COORDS_CSV.name}")
    print("\nAll assertions passed.")
