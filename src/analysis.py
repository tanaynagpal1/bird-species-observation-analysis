r"""
Phase 5 - Guarded analysis.

One function per business question. Each returns a plain DataFrame or dict so
the dashboard can render it directly without re-deriving anything.

Why this module exists
----------------------
The same twelve answers could be written inline in the Streamlit app. They are
not, for one reason: the four guardrails.

Two of the most natural things to do with this dataset - pooling all eleven
parks, and comparing raw sighting counts - each produce a statistically
significant result that is false. Guardrails G1 to G4 prevent that, but a rule
you have to remember is a rule you will eventually forget at 2am on deadline.

So the rules live here, inside the functions, applied before any comparison
happens. `compare_richness()` cannot be called on the full dataset because it
filters to the shared parks itself. The mistake becomes hard to make rather
than merely discouraged.

    G1  Never compare raw counts across habitats. Use per-session rates.
    G2  Habitat comparisons happen WITHIN a park, using only the four parks
        where both habitats were surveyed.
    G3  Use per-session, never per-plot.
    G4  Charts encode adjusted rates, never raw totals.

Run it directly to reproduce every headline figure:

    python src/analysis.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import stats_helpers as sh
from config import PARK_COORDS_CSV, PROCESSED_DIR, SHARED_PARKS

FEATURES_CSV = PROCESSED_DIR / "birds_features.csv"
SESSIONS_CSV = PROCESSED_DIR / "sessions.csv"
SPECIES_CSV = PROCESSED_DIR / "species_profile.csv"

# A species needs this many sightings before a habitat preference means
# anything. Below it, the share is dominated by chance - and, as the
# rarefaction check in q11 shows, by how much surveying happened.
WELL_SAMPLED_MIN = 20

# Rates computed from fewer sessions than this are unstable and must be
# labelled as provisional wherever they are shown. The humidity "<40%" band
# (11.50 species from 12 sessions) is the cautionary example.
MIN_SESSIONS_RELIABLE = 30


# ---------------------------------------------------------------- loading
def load_tables(root: Path | None = None) -> dict[str, pd.DataFrame]:
    """
    Load the four processed tables.

    The dashboard should call this once and cache it. Every question function
    below takes the frames it needs as arguments rather than reading from disk
    itself, so nothing here does hidden IO.
    """
    if root is None:
        rows = pd.read_csv(FEATURES_CSV, encoding="utf-8")
        sessions = pd.read_csv(SESSIONS_CSV, encoding="utf-8")
        species = pd.read_csv(SPECIES_CSV, encoding="utf-8")
        parks = pd.read_csv(PARK_COORDS_CSV, encoding="utf-8")
    else:
        root = Path(root)
        rows = pd.read_csv(root / "data/processed/birds_features.csv", encoding="utf-8")
        sessions = pd.read_csv(root / "data/processed/sessions.csv", encoding="utf-8")
        species = pd.read_csv(root / "data/processed/species_profile.csv", encoding="utf-8")
        parks = pd.read_csv(root / "data/reference/park_coordinates.csv", encoding="utf-8")

    rows["Date"] = pd.to_datetime(rows["Date"])
    sessions["Date"] = pd.to_datetime(sessions["Date"])
    return {"rows": rows, "sessions": sessions, "species": species, "parks": parks}


# ---------------------------------------------------------------- guardrails
def _shared_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Guardrail G2, enforced rather than remembered.

    Any function that compares habitats passes its input through here first.
    There is deliberately no way to opt out: a caller who wants the pooled
    figure has to compute it themselves and will notice they are doing so.
    """
    if "is_shared_park" not in df.columns:
        raise KeyError(
            "Frame has no `is_shared_park` column - it did not come from "
            "features.py. Habitat comparison cannot be guarded without it."
        )
    out = df[df["is_shared_park"]]
    if out.empty:
        raise ValueError(
            f"No rows left after restricting to the shared parks {SHARED_PARKS}. "
            "Check the filters applied before this call."
        )
    return out


def _flag_small(df: pd.DataFrame, count_col: str) -> pd.DataFrame:
    """
    Mark rows whose rate rests on too few sessions to be trusted.

    Normalising for effort removes one bias and introduces another: a rate
    from twelve sessions swings wildly. Rather than silently dropping those
    rows, we label them so the dashboard can grey them out and the reader can
    judge for themselves.
    """
    df = df.copy()
    df["reliable"] = df[count_col] >= MIN_SESSIONS_RELIABLE
    return df



# ---------------------------------------------------------------- Q1 to Q4
def q1_at_risk_by_habitat(sessions: pd.DataFrame) -> dict:
    """
    Q1 - At-risk species rate by habitat, within each shared park.

    Objectives 1 and 5 (conservation, policy). This is the headline.

    Returns a dict with the per-park table, the pooled rates, the
    significance test, and - importantly - the same comparison with Wood
    Thrush removed.

    Why Wood Thrush gets its own figure
    -----------------------------------
    It accounts for 82% of all at-risk sightings. Reporting the pooled 6.2x
    without saying so would imply a general pattern across at-risk birds when
    the data really shows one widespread forest-dependent species dominating
    the records. The robustness figure is part of the answer, not a footnote.
    """
    shared = _shared_only(sessions)

    def _rates(df: pd.DataFrame) -> tuple[float, float]:
        f = df[df.habitat == "Forest"]
        g = df[df.habitat == "Grassland"]
        fr = f.at_risk_sightings.sum() / f.sightings_per_session.sum() * 100
        gr = g.at_risk_sightings.sum() / g.sightings_per_session.sum() * 100
        return fr, gr

    by_park = (
        shared.groupby(["Admin_Unit_Code", "habitat"])
        .apply(lambda g: g.at_risk_sightings.sum() / g.sightings_per_session.sum() * 100,
               include_groups=False)
        .unstack().round(2)
    )
    by_park["forest_higher"] = by_park["Forest"] > by_park["Grassland"]

    f_rate, g_rate = _rates(shared)
    a = shared[shared.habitat == "Forest"].pct_at_risk_per_session.values
    b = shared[shared.habitat == "Grassland"].pct_at_risk_per_session.values
    _, p = sh.mannwhitneyu(a, b)

    return {
        "by_park": by_park,
        "forest_pct": round(f_rate, 2),
        "grassland_pct": round(g_rate, 2),
        "ratio": round(f_rate / g_rate, 1) if g_rate else float("inf"),
        "p_value": p,
        "holds_in_all_parks": bool(by_park["forest_higher"].all()),
        "n_parks": len(by_park),
    }


def q1b_at_risk_without_wood_thrush(rows: pd.DataFrame) -> dict:
    """
    Q1b - The robustness check behind the headline.

    Recomputes the at-risk comparison with Wood Thrush excluded. If the
    finding depends entirely on one species, the report must say so.
    """
    shared = _shared_only(rows)
    no_wt = shared[shared.Common_Name != "Wood Thrush"]

    def _rate(df, hab):
        s = df[df.habitat == hab]
        return s.is_at_risk.mean() * 100 if len(s) else 0.0

    f_all, g_all = _rate(shared, "Forest"), _rate(shared, "Grassland")
    f_no, g_no = _rate(no_wt, "Forest"), _rate(no_wt, "Grassland")

    by_park = (
        no_wt.groupby(["Admin_Unit_Code", "habitat"]).is_at_risk.mean()
        .mul(100).unstack().round(3)
    )
    by_park["forest_higher"] = by_park["Forest"] > by_park["Grassland"]

    wt = rows[rows.Common_Name == "Wood Thrush"]
    total_at_risk = int(rows.is_at_risk.sum())

    return {
        "with_wood_thrush": {"forest": round(f_all, 2), "grassland": round(g_all, 2),
                             "ratio": round(f_all / g_all, 1) if g_all else float("inf")},
        "without_wood_thrush": {"forest": round(f_no, 2), "grassland": round(g_no, 2),
                                "ratio": round(f_no / g_no, 1) if g_no else float("inf")},
        "by_park_without": by_park,
        "parks_agreeing_without": int(by_park["forest_higher"].sum()),
        "wood_thrush_share_pct": round(len(wt) / total_at_risk * 100),
        "wood_thrush_sightings": len(wt),
        "wood_thrush_parks": int(wt.Admin_Unit_Code.nunique()),
        "total_at_risk_sightings": total_at_risk,
        "n_at_risk_species": int(rows[rows.is_at_risk].Scientific_Name.nunique()),
    }


def q2_richness_by_habitat(sessions: pd.DataFrame) -> dict:
    """
    Q2 - Species richness per session by habitat.

    Objective 6. Expected outcome is a NULL result, and that is the finding.

    Computes the comparison twice on purpose. The pooled version is returned
    not because it should be reported as an answer, but because showing the
    contrast is what demonstrates the confound was found rather than missed.
    """
    a_all = sessions[sessions.habitat == "Forest"].species_per_session.values
    b_all = sessions[sessions.habitat == "Grassland"].species_per_session.values
    _, p_all = sh.mannwhitneyu(a_all, b_all)

    shared = _shared_only(sessions)
    a_sh = shared[shared.habitat == "Forest"].species_per_session.values
    b_sh = shared[shared.habitat == "Grassland"].species_per_session.values
    _, p_sh = sh.mannwhitneyu(a_sh, b_sh)

    by_park = (
        shared.groupby(["Admin_Unit_Code", "habitat"])
        .species_per_session.mean().unstack().round(2)
    )
    by_park["forest_higher"] = by_park["Forest"] > by_park["Grassland"]

    return {
        "pooled": {"forest": round(a_all.mean(), 2), "grassland": round(b_all.mean(), 2),
                   "p_value": p_all, "significant": p_all < 0.05,
                   "n_forest": len(a_all), "n_grassland": len(b_all)},
        "within_shared": {"forest": round(a_sh.mean(), 2), "grassland": round(b_sh.mean(), 2),
                          "p_value": p_sh, "significant": p_sh < 0.05,
                          "n_forest": len(a_sh), "n_grassland": len(b_sh)},
        "by_park": by_park,
        "parks_favouring_forest": int(by_park["forest_higher"].sum()),
        "n_parks": len(by_park),
    }


def q3_hotspots(sessions: pd.DataFrame, rows: pd.DataFrame) -> dict:
    """
    Q3 - Top parks and plots by species per session.

    Objective 3 (eco-tourism). G1 and G4: ranked by an effort-adjusted rate.

    The raw-count ranking is returned alongside, because the two disagree and
    the disagreement is the point: MONO leads on total species and falls to
    sixth once effort is accounted for.
    """
    parks = (
        sessions.groupby("Admin_Unit_Code")
        .agg(sessions_run=("species_per_session", "size"),
             species_per_session=("species_per_session", "mean"))
        .round(2)
    )
    parks["distinct_species"] = rows.groupby("Admin_Unit_Code").Scientific_Name.nunique()
    parks = _flag_small(parks, "sessions_run")

    by_rate = parks.sort_values("species_per_session", ascending=False)
    by_raw = parks.sort_values("distinct_species", ascending=False)

    plot_counts = sessions.groupby("Plot_Name").species_per_session.transform("size")
    plots = (
        sessions[plot_counts >= 2]
        .groupby(["Plot_Name", "Admin_Unit_Code", "habitat"])
        .species_per_session.agg(["mean", "size"])
        .rename(columns={"mean": "species_per_session", "size": "visits"})
        .sort_values("species_per_session", ascending=False)
        .round(2)
    )

    return {
        "parks_by_rate": by_rate,
        "parks_by_raw_count": by_raw,
        "top_plots": plots.head(20),
        "ranking_differs": list(by_rate.index[:4]) != list(by_raw.index[:4]),
    }


def q4_specialists(species: pd.DataFrame) -> dict:
    """
    Q4 - Habitat preference per species, shared parks only.

    Objective 2 (land management). The species table was already built on the
    shared parks by features.py, so G2 is satisfied upstream.

    The >=20 sighting threshold is doing more work than it appears: it
    excludes the rare, singly-recorded species whose apparent habitat
    exclusivity is really a survey-effort artefact. See q11.
    """
    well = species[species.well_sampled]
    counts = species.specialist_class.value_counts()

    return {
        "counts": counts,
        "n_well_sampled": len(well),
        "grassland_specialists": well[well.specialist_class == "Grassland specialist"]
            .sort_values("grassland_share_pct", ascending=False),
        "forest_specialists": well[well.specialist_class == "Forest specialist"]
            .sort_values("grassland_share_pct"),
        "generalists": well[well.specialist_class == "Generalist"]
            .sort_values("total_sightings", ascending=False),
        "n_grassland": int(counts.get("Grassland specialist", 0)),
        "n_forest": int(counts.get("Forest specialist", 0)),
        "n_generalist": int(counts.get("Generalist", 0)),
    }



# ---------------------------------------------------------------- Q5 to Q9
def q5_at_risk_species(rows: pd.DataFrame) -> dict:
    """
    Q5 - Which watchlist species occur where.

    Objectives 1 and 5. Computed across all eleven parks, because this is a
    description of where species are - not a habitat comparison - so G2 does
    not apply.

    The `parks` column matters for conservation: a species confined to one
    park is a far sharper priority than one spread across ten.
    """
    at_risk = rows[rows.is_at_risk]

    profile = at_risk.groupby(["Common_Name", "habitat"]).size().unstack(fill_value=0)
    for h in ("Forest", "Grassland"):
        if h not in profile.columns:
            profile[h] = 0
    profile["total"] = profile["Forest"] + profile["Grassland"]
    profile["parks"] = at_risk.groupby("Common_Name").Admin_Unit_Code.nunique()
    profile["pct_of_all_at_risk"] = (profile["total"] / len(at_risk) * 100).round(1)
    profile = profile.sort_values("total", ascending=False)

    by_park = (
        rows.groupby("Admin_Unit_Code")
        .agg(at_risk_pct=("is_at_risk", lambda s: s.mean() * 100),
             sightings=("is_at_risk", "size"))
        .round(2)
    )
    by_park["at_risk_species"] = (
        at_risk.groupby("Admin_Unit_Code").Scientific_Name.nunique()
    )
    by_park = by_park.fillna(0).sort_values("at_risk_pct", ascending=False)

    return {
        "species_profile": profile,
        "by_park": by_park,
        "n_species": int(at_risk.Scientific_Name.nunique()),
        "n_sightings": len(at_risk),
        "dominant_species": profile.index[0],
        "dominant_share_pct": float(profile["pct_of_all_at_risk"].iloc[0]),
    }


def q6_monthly_richness(sessions: pd.DataFrame) -> dict:
    """
    Q6 - Monthly species richness by habitat.

    Objective 6. Descriptive only, for two reasons documented here so nobody
    later mistakes it for a trend:

      1. Forest sampling is uneven across months (June has roughly twice the
         sessions of May or July), so the months are not like-for-like.
      2. Visit number tracks the calendar - later visits fall later in the
         season - so a seasonal decline cannot be separated from a
         repeat-visit decline.
    """
    order = ["May", "June", "July"]
    table = (
        sessions.groupby(["month_name", "habitat"])
        .agg(sessions_run=("species_per_session", "size"),
             species_per_session=("species_per_session", "mean"))
        .round(2).unstack()
    )
    table = table.reindex([m for m in order if m in table.index])

    effort = sessions.groupby(["month_name", "habitat"]).size().unstack(fill_value=0)
    effort = effort.reindex([m for m in order if m in effort.index])
    balance = (effort.max() / effort.min()).round(2)

    return {
        "table": table,
        "effort": effort,
        "effort_imbalance": balance,
        "descriptive_only": True,
        "caveat": ("Forest sampling is uneven across months and visit number tracks "
                   "the calendar, so this is descriptive, not a seasonal trend."),
    }


def q7_time_of_day(sessions: pd.DataFrame) -> dict:
    """
    Q7 - Richness by time-of-day band.

    Objective 6, and the most directly actionable finding in the project.

    Unlike the monthly comparison, hours are spread evenly across sessions, so
    this one carries no effort confound.
    """
    order = ["Early (5-6am)", "Mid (7-8am)", "Late (9-10am)"]
    table = (
        sessions.groupby(["time_band", "habitat"])
        .agg(sessions_run=("species_per_session", "size"),
             species_per_session=("species_per_session", "mean"))
        .round(2).unstack()
    )
    table = table.reindex([b for b in order if b in table.index])

    tests = {}
    for hab in ("Forest", "Grassland"):
        s = sessions[sessions.habitat == hab]
        early = s[s.time_band == order[0]].species_per_session.values
        late = s[s.time_band == order[-1]].species_per_session.values
        if len(early) and len(late):
            _, p = sh.mannwhitneyu(early, late)
            tests[hab] = {
                "early_mean": round(float(early.mean()), 2),
                "late_mean": round(float(late.mean()), 2),
                "gain": round(float(early.mean() - late.mean()), 2),
                "gain_pct": round(float(early.mean() / late.mean() - 1) * 100, 1),
                "p_value": p,
                "significant": p < 0.05,
                "n_early": len(early), "n_late": len(late),
            }

    # Correlation across the whole morning, not just the endpoints.
    trend = {}
    for hab in ("Forest", "Grassland"):
        s = sessions[sessions.habitat == hab].dropna(subset=["start_hour"])
        r, p = sh.spearmanr(s.start_hour.values, s.species_per_session.values)
        trend[hab] = {"rho": round(r, 3), "p_value": p, "significant": p < 0.05}

    return {"table": table, "early_vs_late": tests, "trend": trend}


def q8_weather(sessions: pd.DataFrame) -> dict:
    """
    Q8 - Richness against temperature and humidity bands.

    Objective 6. Bands rather than a scatter of 1,408 points, which would be
    unreadable.

    Note the temperature relationship is NOT monotonic - richness peaks at
    15-20C and falls at both ends - so describing it as "hotter is worse"
    would be wrong at the cold end.
    """
    temp_order = ["<15C", "15-20C", "20-25C", "25-30C", ">30C"]
    hum_order = ["<40%", "40-60%", "60-80%", ">80%"]

    def _band(col: str, order: list[str]) -> pd.DataFrame:
        t = (sessions.groupby(col)
             .agg(sessions_run=("species_per_session", "size"),
                  species_per_session=("species_per_session", "mean"))
             .round(2))
        t = t.reindex([b for b in order if b in t.index])
        return _flag_small(t, "sessions_run")

    correlations = {}
    for hab in ("Forest", "Grassland"):
        s = sessions[sessions.habitat == hab]
        for col in ("Temperature", "Humidity"):
            x = s.dropna(subset=[col])
            r, p = sh.spearmanr(x[col].values, x.species_per_session.values)
            correlations[f"{hab}_{col}"] = {
                "rho": round(r, 3), "p_value": p, "significant": p < 0.05,
            }

    temp = _band("temp_band", temp_order)
    peak = temp[temp["reliable"]]["species_per_session"].idxmax()

    return {
        "temperature": temp,
        "humidity": _band("humidity_band", hum_order),
        "correlations": correlations,
        "temperature_peak_band": peak,
        "monotonic": False,
    }


def q9_conditions(sessions: pd.DataFrame) -> dict:
    """
    Q9 - Richness by sky, wind and disturbance category.

    Objective 6. Disturbance is the strongest environmental effect in the
    dataset, and the one with a clear management implication.

    An anomaly is preserved here rather than smoothed away: "slight effect"
    scores ABOVE "no effect", on large samples in both categories. We do not
    know why. Reporting it as observed is more honest than inventing a
    mechanism.
    """
    out = {}
    for col in ("Sky", "Wind", "Disturbance"):
        t = (sessions.groupby(col)
             .agg(sessions_run=("species_per_session", "size"),
                  species_per_session=("species_per_session", "mean"))
             .round(2).sort_values("species_per_session", ascending=False))
        out[col.lower()] = _flag_small(t, "sessions_run")

    none = sessions[sessions.Disturbance == "No effect on count"].species_per_session.values
    bad = sessions[sessions.Disturbance == "Serious effect on count"].species_per_session.values
    _, p = sh.mannwhitneyu(none, bad)

    dist = out["disturbance"]
    anomaly = False
    if {"Slight effect on count", "No effect on count"} <= set(dist.index):
        anomaly = bool(dist.loc["Slight effect on count", "species_per_session"] >
                       dist.loc["No effect on count", "species_per_session"])

    out["disturbance_test"] = {
        "none_mean": round(float(none.mean()), 2),
        "serious_mean": round(float(bad.mean()), 2),
        "loss_pct": round((1 - bad.mean() / none.mean()) * 100, 1),
        "p_value": p,
        "significant": p < 0.05,
        "n_none": len(none), "n_serious": len(bad),
    }
    out["slight_exceeds_none_anomaly"] = anomaly
    return out


# ---------------------------------------------------------------- Q10 to Q12
def q10_observer_disclosure(sessions: pd.DataFrame) -> dict:
    """
    Q10 - Observer session counts and mean richness.

    Methodology. The three observers differ by 37%, which is larger than the
    habitat effect being measured. That sounds fatal and is not, for one
    reason: they were balanced across habitats and parks.

    Bias needs imbalance to do damage. Even assignment means observer
    differences add variance, not direction. The balance table is therefore
    part of the answer, not supporting detail.
    """
    per_observer = (
        sessions.groupby("Observer")
        .agg(sessions_run=("species_per_session", "size"),
             species_per_session=("species_per_session", "mean"),
             spread=("species_per_session", "std"))
        .round(2).sort_values("species_per_session")
    )

    by_habitat = pd.crosstab(sessions.habitat, sessions.Observer)
    by_park = pd.crosstab(sessions.Admin_Unit_Code, sessions.Observer)

    pairs = {}
    names = sorted(sessions.Observer.dropna().unique())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = sessions[sessions.Observer == names[i]].species_per_session.values
            b = sessions[sessions.Observer == names[j]].species_per_session.values
            _, p = sh.mannwhitneyu(a, b)
            pairs[f"{names[i]} vs {names[j]}"] = p

    lo = per_observer.species_per_session.min()
    hi = per_observer.species_per_session.max()

    # Balance measured WITHIN each habitat: of all the forest sessions, what
    # share did each observer do? Perfect balance is 1/n each.
    #
    # The axis matters. Dividing by the column sums would answer a different
    # question - what share of each OBSERVER's work was forest - which tells
    # you nothing about whether the habitat comparison is safe.
    shares = by_habitat.div(by_habitat.sum(axis=1), axis=0)
    even = 1 / len(names)
    worst_dev = float((shares - even).abs().to_numpy().max())

    return {
        "per_observer": per_observer,
        "by_habitat": by_habitat,
        "by_park": by_park,
        "pairwise_p": pairs,
        "spread_pct": round((hi / lo - 1) * 100, 1),
        "habitat_shares": shares.round(3),
        "max_habitat_share_deviation": round(worst_dev, 4),
        "balanced": worst_dev < 0.05,
    }


def q11_exclusive_species(rows: pd.DataFrame, n_draws: int = 200,
                          seed: int = 0) -> dict:
    """
    Q11 - Species recorded in one habitat only.

    Objective 2. This is the question that needed a third correction.

    The raw answer inside the shared parks is 7 forest-only against 36
    grassland-only, which looks like a strong asymmetry. It is mostly an
    artefact: grassland has roughly four times more sessions there, so four
    times more chances to stumble on a rare bird. Around 40% of the
    "grassland-only" species were recorded exactly once.

    G1 and G2 do not catch this. They normalise rates and control for park,
    but COUNTING DISTINCT SPECIES stays effort-sensitive regardless - rare
    species keep accumulating the longer you look.

    The fix is rarefaction: repeatedly subsample the larger habitat down to
    the smaller one's session count and recount. Only the rarefied figures
    should be reported.
    """
    import numpy as np

    shared = _shared_only(rows)
    f = shared[shared.habitat == "Forest"]
    g = shared[shared.habitat == "Grassland"]

    f_sp = set(f.Scientific_Name)
    g_sp = set(g.Scientific_Name)
    raw = {"forest_only": len(f_sp - g_sp),
           "grassland_only": len(g_sp - f_sp),
           "both": len(f_sp & g_sp)}

    n_f = f.session_id.nunique()
    n_g = g.session_id.nunique()
    small, large = (f, g) if n_f <= n_g else (g, f)
    n_small = min(n_f, n_g)
    small_sp = set(small.Scientific_Name)

    rng = np.random.default_rng(seed)
    large_sessions = large.session_id.unique()
    only_large, only_small = [], []
    for _ in range(n_draws):
        pick = rng.choice(large_sessions, n_small, replace=False)
        sub = set(large[large.session_id.isin(pick)].Scientific_Name)
        only_large.append(len(sub - small_sp))
        only_small.append(len(small_sp - sub))

    forest_is_small = n_f <= n_g
    rarefied = {
        "forest_only": round(float(np.mean(only_small if forest_is_small else only_large)), 1),
        "grassland_only": round(float(np.mean(only_large if forest_is_small else only_small)), 1),
    }

    singletons = {}
    for lab, s, df in (("forest_only", f_sp - g_sp, f),
                       ("grassland_only", g_sp - f_sp, g)):
        c = df[df.Scientific_Name.isin(s)].Scientific_Name.value_counts()
        singletons[lab] = int((c == 1).sum()) if len(c) else 0

    return {
        "raw": raw,
        "rarefied": rarefied,
        "sessions": {"forest": n_f, "grassland": n_g,
                     "ratio": round(max(n_f, n_g) / min(n_f, n_g), 1)},
        "seen_once_only": singletons,
        "n_draws": n_draws,
        "report_raw": False,
        "caveat": ("Raw counts are effort-confounded. Report the rarefied figures "
                   "and name the technique - rarefaction - in the methodology."),
    }


def q12_coverage(sessions: pd.DataFrame) -> dict:
    """
    Q12 - Survey effort by park and habitat.

    Methodology, and the evidence behind every other guardrail. Belongs in the
    dashboard's Data Quality tab: it makes an abstract constraint concrete.
    """
    eff = sessions.groupby(["Admin_Unit_Code", "habitat"]).size().unstack(fill_value=0)
    for h in ("Forest", "Grassland"):
        if h not in eff.columns:
            eff[h] = 0
    eff["total"] = eff["Forest"] + eff["Grassland"]
    eff["both_habitats"] = (eff["Forest"] > 0) & (eff["Grassland"] > 0)
    eff = eff.sort_values("total", ascending=False)

    visits = sessions.groupby(["habitat", "Plot_Name"]).size()
    per_plot = visits.groupby("habitat").mean().round(2)

    duration = (
        sessions.groupby("habitat").session_duration_min
        .agg(["count", "mean", "median", "min", "max"]).round(1)
    )

    usable = int(sessions.is_shared_park.sum())
    return {
        "by_park": eff,
        "visits_per_plot": per_plot,
        "session_duration": duration,
        "parks_with_both": int(eff.both_habitats.sum()),
        "n_parks": len(eff),
        "usable_sessions": usable,
        "total_sessions": len(sessions),
        "usable_pct": round(usable / len(sessions) * 100, 1),
    }


# ---------------------------------------------------------------- verification
def run_all(root: Path | None = None) -> dict:
    """Answer every question and return the results keyed by question id."""
    t = load_tables(root)
    rows, sessions, species = t["rows"], t["sessions"], t["species"]
    return {
        "q1": q1_at_risk_by_habitat(sessions),
        "q1b": q1b_at_risk_without_wood_thrush(rows),
        "q2": q2_richness_by_habitat(sessions),
        "q3": q3_hotspots(sessions, rows),
        "q4": q4_specialists(species),
        "q5": q5_at_risk_species(rows),
        "q6": q6_monthly_richness(sessions),
        "q7": q7_time_of_day(sessions),
        "q8": q8_weather(sessions),
        "q9": q9_conditions(sessions),
        "q10": q10_observer_disclosure(sessions),
        "q11": q11_exclusive_species(rows),
        "q12": q12_coverage(sessions),
    }


if __name__ == "__main__":
    r = run_all()

    print("\nPhase 5 - Guarded analysis")
    print("=" * 64)

    q1, q1b, q2 = r["q1"], r["q1b"], r["q2"]
    print("\nQ1  HEADLINE - at-risk rate by habitat (within shared parks)")
    print(f"    Forest {q1['forest_pct']}%  vs  Grassland {q1['grassland_pct']}%"
          f"   = {q1['ratio']}x    p={q1['p_value']:.3g}")
    print(f"    Holds in all {q1['n_parks']} shared parks: {q1['holds_in_all_parks']}")

    print("\nQ1b ROBUSTNESS - the same, without Wood Thrush")
    print(f"    Wood Thrush is {q1b['wood_thrush_share_pct']}% of all at-risk sightings "
          f"({q1b['wood_thrush_sightings']} of {q1b['total_at_risk_sightings']}), "
          f"in {q1b['wood_thrush_parks']} parks")
    print(f"    Excluding it: {q1b['without_wood_thrush']['ratio']}x, "
          f"direction holds in {q1b['parks_agreeing_without']} of 4 parks")
    print(f"    -> report the Wood Thrush framing, not a general habitat claim")

    print("\nQ2  NULL RESULT - richness per session")
    print(f"    pooled 11 parks : {q2['pooled']['forest']} vs {q2['pooled']['grassland']}"
          f"   p={q2['pooled']['p_value']:.6f}  significant={q2['pooled']['significant']}")
    print(f"    within 4 shared : {q2['within_shared']['forest']} vs {q2['within_shared']['grassland']}"
          f"   p={q2['within_shared']['p_value']:.6f}  significant={q2['within_shared']['significant']}")
    print(f"    direction favours forest in {q2['parks_favouring_forest']} of {q2['n_parks']} parks")

    q3 = r["q3"]
    print("\nQ3  HOTSPOTS")
    print(f"    by species/session : {list(q3['parks_by_rate'].index[:4])}")
    print(f"    by raw count       : {list(q3['parks_by_raw_count'].index[:4])}")
    print(f"    rankings differ    : {q3['ranking_differs']}")

    q4 = r["q4"]
    print("\nQ4  SPECIALISTS")
    print(f"    grassland {q4['n_grassland']}   forest {q4['n_forest']}   "
          f"generalist {q4['n_generalist']}   (of {q4['n_well_sampled']} well-sampled)")

    q5 = r["q5"]
    print("\nQ5  AT-RISK SPECIES")
    print(f"    {q5['n_species']} species, {q5['n_sightings']} sightings; "
          f"{q5['dominant_species']} is {q5['dominant_share_pct']}% of them")

    q7 = r["q7"]
    print("\nQ7  TIME OF DAY")
    for hab, d in q7["early_vs_late"].items():
        print(f"    {hab:<10} early {d['early_mean']} vs late {d['late_mean']}"
              f"  (+{d['gain']}, {d['gain_pct']}%)  p={d['p_value']:.3g}"
              f"  {'SIGNIFICANT' if d['significant'] else 'not significant'}")

    q8, q9 = r["q8"], r["q9"]
    print("\nQ8  WEATHER")
    print(f"    richness peaks at {q8['temperature_peak_band']} - not monotonic")
    print("\nQ9  DISTURBANCE")
    d = q9["disturbance_test"]
    print(f"    none {d['none_mean']} vs serious {d['serious_mean']}"
          f"  = {d['loss_pct']}% loss   p={d['p_value']:.3g}")
    print(f"    unexplained anomaly (slight > none): {q9['slight_exceeds_none_anomaly']}")

    q10 = r["q10"]
    print("\nQ10 OBSERVER")
    print(f"    spread {q10['spread_pct']}%   balanced across habitats: {q10['balanced']}")

    q11 = r["q11"]
    print("\nQ11 EXCLUSIVE SPECIES")
    print(f"    raw       : forest {q11['raw']['forest_only']}  "
          f"grassland {q11['raw']['grassland_only']}   <- effort-confounded, do not report")
    print(f"    rarefied  : forest {q11['rarefied']['forest_only']}  "
          f"grassland {q11['rarefied']['grassland_only']}   <- report this")
    print(f"    ({q11['sessions']['ratio']}x more grassland sessions; "
          f"{q11['seen_once_only']['grassland_only']} grassland-only species seen once)")

    q12 = r["q12"]
    print("\nQ12 COVERAGE")
    print(f"    {q12['parks_with_both']} of {q12['n_parks']} parks have both habitats")
    print(f"    {q12['usable_sessions']:,} of {q12['total_sessions']:,} sessions "
          f"usable for habitat comparison ({q12['usable_pct']}%)")

    print("\nAll twelve questions answered.")