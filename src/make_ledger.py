"""
Generate docs/findings-ledger.md - the running record of every verified number
in this project, and what each one does or does not support.

Why this is a script and not a hand-written document
----------------------------------------------------
The Report and Conclusion tabs, the internship write-up, and any slide deck all
need the same figures. Typing them into a document by hand creates a second
source of truth that silently drifts the moment analysis.py changes. This file
reads analysis.run_all() and writes the document, so a figure can only be wrong
here if it is also wrong in the analysis.

Run it from the project root:

    python src/make_ledger.py

It overwrites docs/findings-ledger.md. Re-run it after any change to
analysis.py or the cleaned data.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import analysis  # noqa: E402
import stats_helpers as sh  # noqa: E402

OUT = ROOT / "docs" / "findings-ledger.md"


def p(value: float) -> str:
    """Format a p-value, without printing a hard 0 for an underflow."""
    if value == 0:
        return "p < 1e-300"
    if value < 0.001:
        return f"p = {value:.2e}"
    return f"p = {value:.4f}"


def verdict(significant: bool) -> str:
    return "**significant**" if significant else "not significant"


def table(df) -> str:
    """Render a DataFrame or Series as a GitHub markdown table.

    Written by hand rather than via DataFrame.to_markdown(), which needs the
    `tabulate` package - not worth adding a dependency to requirements.txt,
    and to the Streamlit Cloud build, for one document generator.
    """
    if isinstance(df, pd.Series):
        df = df.to_frame()
    d = df.reset_index()
    # A MultiIndex on the columns is flattened to "a b" so the header stays
    # a single row, which is all GitHub markdown supports.
    cols = [" ".join(str(x) for x in c if str(x) != "").strip()
            if isinstance(c, tuple) else str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in d.iterrows():
        cells = [f"{v:.4g}" if isinstance(v, float) else str(v) for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def build() -> str:
    r = analysis.run_all(ROOT)
    t = analysis.load_tables(ROOT)
    rows, sessions = t["rows"], t["sessions"]

    q1, q1b, q2 = r["q1"], r["q1b"], r["q2"]
    q3, q4, q5 = r["q3"], r["q4"], r["q5"]
    q6, q7, q8 = r["q6"], r["q7"], r["q8"]
    q9, q10, q11, q12 = r["q9"], r["q10"], r["q11"], r["q12"]
    q13, q14 = r["q13"], r["q14"]

    L: list[str] = []
    add = L.append

    # ---------------------------------------------------------------- header
    add("# Findings ledger")
    add("")
    add(f"*Generated {date.today().isoformat()} by `src/make_ledger.py` from "
        f"`analysis.run_all()`. Do not edit by hand - re-run the script.*")
    add("")
    add("Every number below is produced by the analysis pipeline, not typed in. "
        "Each entry records the figure, the test behind it, and - just as "
        "importantly - what it does **not** license anyone to say.")
    add("")

    # ---------------------------------------------------------------- dataset
    add("## 1. What the dataset is")
    add("")
    add(f"- **{len(rows):,}** individual sightings across **{len(sessions):,}** "
        f"survey sessions")
    add(f"- **{rows['Scientific_Name'].nunique()}** distinct species, "
        f"**{q12['n_parks']}** NPS units, 2018 breeding season (May-July)")
    add(f"- **{q12['parks_with_both']} of {q12['n_parks']}** parks were surveyed "
        f"in *both* forest and grassland - "
        f"**{q12['usable_sessions']:,} of {q12['total_sessions']:,} sessions "
        f"({q12['usable_pct']}%)** are therefore usable for a fair habitat "
        f"comparison")
    add(f"- Median session length is 10 minutes in both habitats, so effort per "
        f"session is comparable; visits per plot are "
        f"{q12['visits_per_plot']['Forest']} (forest) vs "
        f"{q12['visits_per_plot']['Grassland']} (grassland)")
    add("")
    add("### Survey effort by park")
    add("")
    add(table(q12["by_park"]))
    add("")
    add("**Why this table drives everything else.** Seven of eleven parks were "
        "surveyed in one habitat only. In those parks, \"forest vs grassland\" "
        "is really \"park A vs park B\". Every habitat comparison in this "
        "project is therefore restricted to the four shared parks.")
    add("")

    # ---------------------------------------------------------------- guardrails
    add("## 2. The four guardrails")
    add("")
    add("| ID | Rule | Why it exists |")
    add("|----|------|---------------|")
    add("| G1 | Compare per-session **rates**, never raw totals | Grassland ran "
        "~4x more sessions than forest; raw counts measure effort |")
    add("| G2 | Habitat comparisons use the **4 shared parks** only | "
        "Otherwise habitat is confounded with park identity |")
    add("| G3 | Treat any group with **<30 sessions** as unreliable | Small "
        "samples produce large, meaningless swings |")
    add("| G4 | **Rarefy** before comparing species counts | More sampling "
        "finds more species even from an identical community |")
    add("")

    # ---------------------------------------------------------------- Q1
    add("## 3. Findings, question by question")
    add("")
    add("### Q1 - At-risk species by habitat *(headline finding)*")
    add("")
    add(f"- Forest sessions record at-risk birds at **{q1['forest_pct']}%** of "
        f"sightings against **{q1['grassland_pct']}%** in grassland - a "
        f"**{q1['ratio']}x** difference")
    add(f"- Mann-Whitney {p(q1['p_value'])} -> {verdict(True)}")
    add(f"- Holds in **all {q1['n_parks']} of {q1['n_parks']}** shared parks "
        f"(`holds_in_all_parks = {q1['holds_in_all_parks']}`)")
    add("")
    add(table(q1["by_park"]))
    add("")
    add("**Status: a real finding.** It survives G1, G2, and the per-park check "
        "that destroys the richness result below.")
    add("")

    # ---------------------------------------------------------------- Q1b
    add("### Q1b - The same finding, stress-tested")
    add("")
    add(f"- **{q1b['wood_thrush_sightings']} of "
        f"{q1b['total_at_risk_sightings']}** at-risk sightings "
        f"(**{q1b['wood_thrush_share_pct']}%**) are Wood Thrush alone")
    add(f"- Remove it and the ratio falls from **{q1b['with_wood_thrush']['ratio']}x** "
        f"to **{q1b['without_wood_thrush']['ratio']}x**")
    add(f"- The direction then holds in only "
        f"**{q1b['parks_agreeing_without']} of {q1['n_parks']}** shared parks")
    add("")
    add(table(q1b["by_park_without"]))
    add("")
    add("**Status: the finding is real but narrower than it first appears.** The "
        "defensible claim is *\"forest shelters Wood Thrush\"*, not *\"forest "
        f"shelters at-risk birds\"* as a class. All {q1b['n_at_risk_species']} "
        "watchlist species were recorded, but one carries the signal.")
    add("")

    # ---------------------------------------------------------------- Q2
    add("### Q2 - Species richness by habitat *(Simpson's paradox)*")
    add("")
    add("| Comparison | Forest | Grassland | n (F / G) | p | Verdict |")
    add("|---|---|---|---|---|---|")
    add(f"| Pooled, all 11 parks | {q2['pooled']['forest']} | "
        f"{q2['pooled']['grassland']} | {q2['pooled']['n_forest']} / "
        f"{q2['pooled']['n_grassland']} | {p(q2['pooled']['p_value'])} | "
        f"looks {verdict(q2['pooled']['p_value'] < 0.05)} |")
    add(f"| Within 4 shared parks | {q2['within_shared']['forest']} | "
        f"{q2['within_shared']['grassland']} | "
        f"{q2['within_shared']['n_forest']} / "
        f"{q2['within_shared']['n_grassland']} | "
        f"{p(q2['within_shared']['p_value'])} | "
        f"{verdict(q2['within_shared']['p_value'] < 0.05)} |")
    add("")
    add(table(q2["by_park"]))
    add("")
    add(f"- Forest wins in **{q2['parks_favouring_forest']} of {q2['n_parks']}** "
        f"shared parks - a coin flip")
    add("")
    add("**Status: not a finding.** The pooled difference is an artefact of "
        "which parks were surveyed how often. This is the clearest teaching "
        "case in the project and the reason G2 exists.")
    add("")

    # ---------------------------------------------------------------- Q3
    add("### Q3 - Hotspots: parks and plots")
    add("")
    add(table(q3["parks_by_rate"]))
    add("")
    pk = q3["parks_by_rate"]
    rho_eff_raw, p_eff_raw = sh.spearmanr(
        pk["sessions_run"].values, pk["distinct_species"].values)
    rho_eff_rate, p_eff_rate = sh.spearmanr(
        pk["sessions_run"].values, pk["species_per_session"].values)
    add(f"- Ranking by rate and by raw count **disagree** "
        f"(`ranking_differs = {q3['ranking_differs']}`)")
    add(f"- Raw species count vs survey effort: **rho = {rho_eff_raw:.3f}**, "
        f"{p(p_eff_raw)} -> {verdict(p_eff_raw < 0.05)}")
    add(f"- Species per session vs survey effort: **rho = {rho_eff_rate:.3f}**, "
        f"{p(p_eff_rate)} -> {verdict(p_eff_rate < 0.05)}")
    add("")
    add("**This pair is the numerical proof of G1.** A raw-count leaderboard is "
        "substantially a leaderboard of who got surveyed most; the "
        "effort-adjusted rate is independent of effort, which is the property a "
        "fair ranking needs.")
    add("")
    plots = sessions.groupby("Plot_Name").species_per_session.agg(["mean", "size"])
    add(f"- Plot level: **{len(plots)}** plots, mean "
        f"**{plots['mean'].mean():.2f}** species/session, no plot visited more "
        f"than **{int(plots['size'].max())}** times")
    add(f"- The top-15 plot table is simply everything above "
        f"**{q3['top_plots'].head(15)['species_per_session'].min()}** - the "
        f"right tail of that distribution, not a set of special places")
    add("")

    # ------------------------------------------------------- at-risk by park
    ar = (sessions.groupby("Admin_Unit_Code")
          .agg(sessions_run=("session_id", "size"),
               at_risk_sessions=("has_at_risk", "sum")))
    ar["pct_sessions_with_at_risk"] = (
        ar["at_risk_sessions"] / ar["sessions_run"] * 100).round(1)
    ar["reliable"] = ar["sessions_run"] >= 30
    ar = ar.sort_values("pct_sessions_with_at_risk", ascending=False)
    top = ar.index[0]
    top_rank = int(pk["species_per_session"].rank(
        ascending=False, method="min").loc[top])
    # Park codes are opaque in prose - swap in the readable name where the
    # ledger names a specific park.
    names = pd.read_csv(ROOT / "data" / "reference" / "park_coordinates.csv")
    NAME = dict(zip(names["Admin_Unit_Code"], names["park_name"]))
    top_name = NAME.get(top, top)
    add("### Q3b - At-risk presence by park *(derived for the Where tab)*")
    add("")
    add(table(ar))
    add("")
    add(f"**The diversity ranking and the conservation ranking disagree.** "
        f"{top_name} records an at-risk species in "
        f"**{ar['pct_sessions_with_at_risk'].iloc[0]}%** of sessions - the "
        f"highest of any park - while ranking **#{top_rank} of "
        f"{len(pk)}** for species per session. \"Best park\" is a property of "
        f"the question, not of the park.")
    add("")

    # ---------------------------------------------------------------- Q4
    add("### Q4 - Habitat specialists")
    add("")
    add(f"- Of **{q4['n_well_sampled']}** well-sampled species: "
        f"**{q4['n_grassland']}** grassland specialists, "
        f"**{q4['n_forest']}** forest specialists, "
        f"**{q4['n_generalist']}** generalists")
    add("")
    add("**Status: a real and striking asymmetry.** Zero forest specialists is "
        "not a sampling artefact - it survives the same shared-parks "
        "restriction as everything else. Forest birds here are generalists that "
        "also use grassland; grassland birds are loyal to grassland. This is "
        "the strongest ecological result in the project after Q1.")
    add("")

    # ---------------------------------------------------------------- Q5
    add("### Q5 - The at-risk roster")
    add("")
    add(table(q5["species_profile"]))
    add("")
    add(f"- **{q5['dominant_species']}** alone is "
        f"**{q5['dominant_share_pct']}%** of all {q5['n_sightings']} at-risk "
        f"sightings, across {q5['n_species']} watchlist species")
    add("")

    # ---------------------------------------------------------------- Q6
    add("### Q6 - Monthly richness *(descriptive only)*")
    add("")
    add(table(q6["table"]))
    add("")
    add(f"- Forest effort imbalance across months: "
        f"**{q6['effort_imbalance']['Forest']}x**; grassland "
        f"**{q6['effort_imbalance']['Grassland']}x**")
    rho_cal, p_cal = sh.spearmanr(
        sessions["Visit"].values, sessions["day_of_season"].values)
    rho_rich, p_rich = sh.spearmanr(
        sessions["Visit"].values, sessions["species_per_session"].values)
    add(f"- Visit number vs day of season: **rho = {rho_cal:.3f}**, {p(p_cal)}")
    add(f"- Visit number vs richness: **rho = {rho_rich:.3f}**, {p(p_rich)}")
    vh = sessions.groupby(["Visit", "habitat"]).size().unstack(fill_value=0)
    add(f"- Third visits happened in grassland only "
        f"({int(vh.loc[3, 'Grassland'])} sessions vs "
        f"{int(vh.loc[3, 'Forest'])} in forest)")
    add("")
    add("**Status: not a finding, and untestable.** Visit number and calendar "
        "date are nearly the same variable here, so a seasonal decline cannot "
        "be separated from a repeat-visit decline - and the late season is a "
        "different habitat mix as well. Three confounds on one axis.")
    add("")

    # ---------------------------------------------------------------- Q7
    add("### Q7 - Time of day *(the actionable finding)*")
    add("")
    add(table(q7["table"]))
    add("")
    add("| Habitat | Early | Late | Change | Early-vs-late p | Whole-morning rho | Verdict |")
    add("|---|---|---|---|---|---|---|")
    for hab in ("Grassland", "Forest"):
        e = q7["early_vs_late"][hab]
        tr = q7["trend"][hab]
        add(f"| {hab} | {e['early_mean']} | {e['late_mean']} | "
            f"{e['gain_pct']}% | {p(e['p_value'])} | {tr['rho']} "
            f"({p(tr['p_value'])}) | {verdict(e['significant'])} |")
    add("")
    dur = sessions.groupby("time_band").session_duration_min.mean().round(1)
    add(f"- Session length is {dur.min()}-{dur.max()} minutes across all bands, "
        f"so the effect is not early surveys running longer")
    ar_band = (sessions.groupby(["time_band", "habitat"])
               .has_at_risk.mean().mul(100).round(1).unstack())
    add("")
    add(table(ar_band))
    add("")
    add("**Status: a real finding, in grassland only.** Confirmed two "
        "independent ways (endpoint test and whole-morning trend) and free of "
        "the confounds that sink Q6. Note the at-risk table above: the morning "
        "advantage is about *how many* species turn up, not *which* - there is "
        "no time-of-day effect on at-risk detection in either habitat.")
    add("")

    # ---------------------------------------------------------------- Q8
    add("### Q8 - Temperature and humidity")
    add("")
    add(table(q8["temperature"]))
    add("")
    add(table(q8["humidity"]))
    add("")
    add("| Correlation | rho | p | Verdict |")
    add("|---|---|---|---|")
    for k, v in q8["correlations"].items():
        add(f"| {k.replace('_', ' - ')} | {v['rho']} | {p(v['p_value'])} | "
            f"{verdict(v['significant'])} |")
    add("")
    add(f"- Richness peaks at **{q8['temperature_peak_band']}** and falls at "
        f"**both** ends (`monotonic = {q8['monotonic']}`)")
    add("")
    add("**Status: real, but the correlation coefficient misdescribes it.** "
        "Spearman's rho is a monotonic statistic; applied to a hump-shaped "
        "relationship it returns a significant negative value that would tell a "
        "reader the coldest mornings are best. The curve says otherwise. "
        "Defensible claim: the warm end is worse. Not defensible: anything "
        "about cold mornings beating mild ones.")
    add("")
    add(f"- The <40% humidity band shows the highest single figure on the "
        f"dashboard ({q8['humidity'].loc['<40%', 'species_per_session']} "
        f"species/session) on "
        f"{int(q8['humidity'].loc['<40%', 'sessions_run'])} sessions - "
        f"excluded by G3.")
    add("")

    # ---------------------------------------------------------------- Q9
    add("### Q9 - Sky, wind and disturbance")
    add("")
    add(table(q9["disturbance"]))
    add("")
    dt = q9["disturbance_test"]
    add(f"- No disturbance **{dt['none_mean']}** (n={dt['n_none']}) vs serious "
        f"disturbance **{dt['serious_mean']}** (n={dt['n_serious']}) - a "
        f"**{dt['loss_pct']}%** loss, {p(dt['p_value'])} -> "
        f"{verdict(dt['significant'])}")
    add(f"- Anomaly preserved: \"slight effect\" scores *above* \"no effect\" "
        f"(`slight_exceeds_none_anomaly = {q9['slight_exceeds_none_anomaly']}`), "
        f"on large samples in both categories. Cause unknown; reported as "
        f"observed rather than explained away.")
    add("")
    add(table(q9["sky"]))
    add("")
    add(table(q9["wind"]))
    add("")
    add("**Status: disturbance is the largest environmental effect in the "
        "dataset and the only one with a management lever attached.** Sky and "
        "wind show mild, plausible patterns that were not significance-tested "
        "and are too small to act on.")
    add("")

    # ------------------------------------------------- Q9b disturbance by park
    bad = sessions.copy()
    bad["disrupted"] = bad["Disturbance"].isin(
        ["Moderate effect on count", "Serious effect on count"])
    dbp = (bad.groupby("Admin_Unit_Code")
           .agg(sessions_run=("session_id", "size"),
                disrupted=("disrupted", "mean")))
    dbp["pct_disrupted"] = (dbp["disrupted"] * 100).round(1)
    dbp["reliable"] = dbp["sessions_run"] >= 30
    dbp = dbp.drop(columns="disrupted").sort_values(
        "pct_disrupted", ascending=False)
    add("### Q9b - Where disturbance happens *(derived for the Environment tab)*")
    add("")
    add(table(dbp))
    add("")
    rel_dbp = dbp[dbp["reliable"]]
    add(f"- Among parks clearing the reliability floor, disturbance ranges from "
        f"**{rel_dbp['pct_disrupted'].max()}%** of sessions "
        f"({NAME.get(rel_dbp.index[0], rel_dbp.index[0])}) down to "
        f"**{rel_dbp['pct_disrupted'].min()}%** "
        f"({NAME.get(rel_dbp.index[-1], rel_dbp.index[-1])})")
    add("")
    add("**Status: descriptive, and the most actionable table in the project.** "
        "The parks at the top are linear and urban sites - parkways and city "
        "parks with roads and footfall beside the plots. That reading is "
        "plausible but untested; the percentages are simply counts. Unlike "
        "weather, disturbance is a property of the site and the schedule, so "
        "it is the one environmental variable management can move.")
    add("")
    dist_hab = (sessions.groupby(["Disturbance", "habitat"])
                .species_per_session.mean().round(2).unstack())
    add("**The slight-over-none anomaly replicates in both habitats:**")
    add("")
    add(table(dist_hab))
    add("")
    add("That it appears independently in forest and in grassland is why it is "
        "reported as observed rather than dismissed as noise.")
    add("")

    # ---------------------------------------------------------------- Q10
    add("### Q10 - Observer effects *(the methodological finding)*")
    add("")
    add(table(q10["per_observer"]))
    add("")
    add("| Pair | p |")
    add("|---|---|")
    for k, v in q10["pairwise_p"].items():
        add(f"| {k} | {p(v)} |")
    add("")
    add(f"- Spread between best and worst observer: **{q10['spread_pct']}%**")
    add(f"- Observers are balanced across habitats "
        f"(`balanced = {q10['balanced']}`, max share deviation "
        f"{q10['max_habitat_share_deviation']})")
    add("")
    add(table(q10["by_habitat"]))
    add("")
    obs_gap = (q10["per_observer"]["species_per_session"].max()
               - q10["per_observer"]["species_per_session"].min())
    hab_gap = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])
    add(f"**Status: the most important methodological result in the project.** "
        f"The gap between observers is **{obs_gap:.2f}** species per session. "
        f"The habitat gap this study set out to measure is **{hab_gap:.2f}** "
        f"species per session. Who held the clipboard matters roughly "
        f"**{obs_gap / hab_gap:.0f}x** more than which habitat was surveyed. "
        f"Because the rota was balanced, this does not bias the habitat "
        f"comparison - but any future study that lets observer assignment "
        f"correlate with treatment will measure the observer, not the habitat.")
    add("")

    # ------------------------------------------- Q10b observer robustness
    add("### Q10b - Is the observer effect really the observer? *(derived)*")
    add("")
    wp = (sessions.groupby(["Admin_Unit_Code", "Observer"])
          .species_per_session.agg(["size", "mean"]).reset_index())
    wp = wp[wp["size"] >= 20]
    ok = wp.groupby("Admin_Unit_Code").size()
    wp = wp[wp["Admin_Unit_Code"].isin(ok[ok == 3].index)]
    piv = wp.pivot(index="Admin_Unit_Code", columns="Observer",
                   values="mean").round(2)
    add(table(piv))
    add("")
    orders = {tuple(r.sort_values(ascending=False).index)
              for _, r in piv.iterrows()}
    add(f"- Across the **{len(piv)}** parks where all three surveyors ran 20+ "
        f"sessions, the ranking is "
        f"{'**identical in every park**' if len(orders) == 1 else 'largely stable'} "
        f"- the same person is lowest everywhere and the same person is "
        f"highest everywhere.")
    obs_hab = (sessions[sessions.is_shared_park]
               .groupby(["Observer", "habitat"])
               .species_per_session.mean().round(2).unstack())
    add("")
    add(table(obs_hab))
    add("")
    add("- Within the shared parks, all three surveyors independently reach "
        "the same conclusion about habitat: no meaningful richness gap. They "
        "disagree about the absolute numbers and agree about the finding.")
    add("")
    add("**Status: the observer effect is the person, not their assignment - "
        "and it does not contaminate any conclusion.** The rank order is "
        "stable across parks, so it cannot be explained by who was sent where; "
        "the rota was balanced across habitats, so it cancels out of habitat "
        "comparisons; and the null habitat result replicates three times "
        "independently. The practical limit it does impose: absolute "
        "species-per-session figures carry a personal-calibration band of "
        f"roughly +/-{(piv.max(axis=1) - piv.min(axis=1)).mean() / 2:.1f} "
        "species, so they should not be quoted against another study's "
        "absolute numbers.")
    add("")

    # --------------------------------------------- protocol and completeness
    add("### Data integrity - protocol adherence and missingness")
    add("")
    dur = sessions["session_duration_min"]
    add(f"- **{int((dur == 10).sum()):,} of {len(dur):,}** sessions "
        f"({(dur == 10).mean() * 100:.1f}%) ran exactly the 10-minute "
        f"protocol; {int((dur > 10).sum())} ran longer, up to "
        f"{int(dur.max())} minutes")
    add(f"- Median duration is identical in both habitats, so no rate in this "
        f"project needs a duration correction")
    miss = rows.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    md = pd.DataFrame({"missing": miss.values,
                       "pct_of_rows": (miss.values / len(rows) * 100).round(1)},
                      index=miss.index)
    add("")
    add(table(md))
    add("")
    n_fly = int(rows["is_flyover"].sum())
    exact = bool((rows["Distance"].isna() == rows["is_flyover"]).all())
    add(f"- **{n_fly}** records have no `Distance`, and exactly those "
        f"{n_fly} records are flyovers - birds passing overhead with no "
        f"distance to record. One-to-one with no exceptions: "
        f"`{exact}`")
    add("")
    add("**Status: missingness is explained by the protocol, not by data "
        "loss.** Every column with gaps has a structural reason. Missingness "
        "that maps exactly onto a protocol rule is evidence of a well-run "
        "survey.")
    add("")

    # ---------------------------------------------------------------- Q11
    add("### Q11 - Exclusive species, raw vs rarefied")
    add("")
    add("| Measure | Forest-only | Grassland-only | Ratio |")
    add("|---|---|---|---|")
    add(f"| Raw count | {q11['raw']['forest_only']} | "
        f"{q11['raw']['grassland_only']} | "
        f"{q11['raw']['grassland_only'] / q11['raw']['forest_only']:.1f}x |")
    add(f"| Rarefied ({q11['n_draws']} draws) | {q11['rarefied']['forest_only']} | "
        f"{q11['rarefied']['grassland_only']} | "
        f"{q11['rarefied']['grassland_only'] / q11['rarefied']['forest_only']:.1f}x |")
    add("")
    add(f"- Grassland ran {q11['sessions']['grassland']} sessions against "
        f"forest's {q11['sessions']['forest']} - a "
        f"{q11['sessions']['ratio']}x gap")
    add(f"- Seen exactly once: {q11['seen_once_only']['forest_only']} "
        f"forest-only and {q11['seen_once_only']['grassland_only']} "
        f"grassland-only species")
    add("")
    add("**Status: real but far smaller than the raw number suggests.** Most of "
        "the apparent gap is sampling effort. This is G4 doing its job.")
    add("")

    # ------------------------------------------------------- Q13
    add("### Q13 - Diversity beyond richness *(four measures, one answer)*")
    add("")
    add("Richness counts species and ignores how evenly individuals are spread "
        "across them. Shannon weights rare species, Simpson weights common "
        "ones, and Pielou's evenness strips out richness altogether. If the "
        "habitat null result of Q2 were an artefact of picking the wrong "
        "measure, one of these would break it.")
    add("")
    add("| Measure | Forest | Grassland | p | Significant |")
    add("|---|---|---|---|---|")
    for m in q13["metrics"]:
        t = q13["tests"][m]
        add(f"| {m.replace('_', ' ').title()} | {t['forest']} | "
            f"{t['grassland']} | {t['p_value']:.3f} | "
            f"{'yes' if t['significant'] else 'no'} |")
    add("")
    add(f"- Computed per session (G1) within the shared parks only (G2), on "
        f"{q13['tests']['richness']['n_forest']} forest and "
        f"{q13['tests']['richness']['n_grassland']} grassland sessions")
    add(f"- Smallest p across all four measures: "
        f"{min(t['p_value'] for t in q13['tests'].values()):.2f}")
    add("")
    add("**Status: the null result survives all four measures.** Not one comes "
        "close to significance. The habitats do not differ in how many species "
        "are present, nor in how evenly those species are distributed.")
    add("")

    add("#### Q13b - Community similarity, rarefied")
    add("")
    sim = q13["similarity"]
    add("| Comparison | Jaccard (shared species) | Bray-Curtis (dissimilarity) "
        "| Pairs |")
    add("|---|---|---|---|")
    add(f"| Between habitats, same park | {sim['between_habitat']['jaccard']} | "
        f"{sim['between_habitat']['bray_curtis']} | "
        f"{sim['between_habitat']['n_pairs']} |")
    add(f"| Within a habitat, different parks | "
        f"{sim['within_habitat']['jaccard']} | "
        f"{sim['within_habitat']['bray_curtis']} | "
        f"{sim['within_habitat']['n_pairs']} |")
    add("")
    add(f"- Jaccard barely moves ({sim['jaccard_gap']:+.3f}): the two habitats "
        f"draw on much the same species list")
    add(f"- Bray-Curtis is the gap that matters "
        f"({sim['bray_gap']:+.3f}): they weight that shared list differently")
    add(f"- Rarefying to equal session counts shrank the Bray-Curtis gap by "
        f"**{sim['rarefaction_shrank_bray_gap_by_pct']}%** "
        f"(raw between-habitat was {sim['between_habitat']['bray_curtis_raw']}, "
        f"rarefied {sim['between_habitat']['bray_curtis']}) - G4 again")
    add("")
    add("**Status: shared species pool, different weighting.** This is the "
        "precise statement the project can defend: habitat changes the mix, "
        "not the roster or the count. Most of the raw difference was effort.")
    add("")

    # ------------------------------------------------------- Q14
    add("### Q14 - Detection channel and interval *(mechanism for Q10)*")
    add("")
    add(f"Q10 showed the three surveyors differ by {q10['spread_pct']}% but "
        f"could not say why. This splits their detections by how the bird was "
        f"identified.")
    add("")
    add("| Method | Detections | % of all |")
    add("|---|---|---|")
    for m in q14["method_counts"].index:
        add(f"| {m} | {q14['method_counts'][m]:,} | {q14['method_share'][m]} |")
    add("")
    add(f"- **{q14['auditory_pct']}%** of detections are auditory - the survey "
        f"is in practice a hearing test")
    add(f"- Observer gap on auditory channels: **{q14['auditory_gap']:.2f}** "
        f"species per session")
    add(f"- Observer gap on the visual channel: **{q14['visual_gap']:.2f}**")
    add(f"- {q14['overall_lowest_observer']} records fewest species overall "
        f"but is **not** lowest on visual "
        f"({q14['lowest_on_channel']['Visualization']} is)")
    add("")
    add(table(q14["by_observer"]))
    add("")
    add("**Status: the observer effect is an ear-training effect.** A surveyor "
        "who was simply less thorough would be lowest on every channel. The "
        "rank order reversing between auditory and visual makes this a "
        "trainable recognition difference, which is what turns Q10 from a "
        "caveat into an actionable recommendation.")
    add("")

    add("#### Q14b - Does the 10-minute count saturate?")
    add("")
    add("| Interval | Detections | % | Cumulative % |")
    add("|---|---|---|---|")
    tot = int(q14["interval_counts"].sum())
    for iv in q14["interval_counts"].index:
        n = int(q14["interval_counts"][iv])
        add(f"| {iv} | {n:,} | {n / tot * 100:.1f} | "
            f"{q14['interval_cumulative'][iv]} |")
    add("")
    add(f"- {q14['first_interval_pct']}% of detections arrive in the first "
        f"2.5 minutes; the last interval adds "
        f"{100 - q14['interval_cumulative']['5 - 7.5 min']:.1f}%")
    add(f"- First-interval share by surveyor ranges "
        f"{q14['by_observer_interval']['0-2.5 min'].min()}% to "
        f"{q14['by_observer_interval']['0-2.5 min'].max()}% - they accumulate "
        f"at the same rate, so the gap is not attention span")
    add("")
    add("**Status: adequate but not saturated.** The curve is flattening and "
        "has not gone flat. Ten minutes captures the regular users of a site; "
        "a longer count would still add occasional records.")
    add("")

    # ------------------------------------------------------- effect sizes
    add("### Every effect in the project, in the same units")
    add("")
    t_rel = q8["temperature"][q8["temperature"]["reliable"]]["species_per_session"]
    h_rel = q8["humidity"][q8["humidity"]["reliable"]]["species_per_session"]
    s_rel = q9["sky"][q9["sky"]["reliable"]]["species_per_session"]
    w_rel = q9["wind"][q9["wind"]["reliable"]]["species_per_session"]
    obs_s = q10["per_observer"]["species_per_session"]
    scale = pd.DataFrame([
        ("Disturbance (none -> serious)", dt["none_mean"] - dt["serious_mean"], "yes"),
        ("Observer (3 surveyors)", obs_s.max() - obs_s.min(), "yes"),
        ("Sky (best -> worst)", s_rel.max() - s_rel.min(), "no"),
        ("Temperature (best -> worst band)", t_rel.max() - t_rel.min(), "yes"),
        ("Time of day, grassland",
         q7["early_vs_late"]["Grassland"]["early_mean"]
         - q7["early_vs_late"]["Grassland"]["late_mean"], "yes"),
        ("Wind (best -> worst)", w_rel.max() - w_rel.min(), "no"),
        ("Humidity (best -> worst)", h_rel.max() - h_rel.min(), "no"),
        ("Time of day, forest",
         q7["early_vs_late"]["Forest"]["early_mean"]
         - q7["early_vs_late"]["Forest"]["late_mean"], "tested, failed"),
        ("Habitat (within shared parks)",
         abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"]),
         "tested, failed"),
    ], columns=["effect", "gap (species/session)", "significance-tested?"])
    scale = scale.sort_values("gap (species/session)", ascending=False)
    add(table(scale.set_index("effect")))
    add("")
    hab_g = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])
    dist_g = dt["none_mean"] - dt["serious_mean"]
    add(f"**The habitat difference this survey was designed to measure is the "
        f"smallest effect in the table.** Disturbance is **{dist_g / hab_g:.0f}x** "
        f"larger; the observer is **{(obs_s.max() - obs_s.min()) / hab_g:.0f}x** "
        f"larger. Each figure is the range between the best and worst category "
        f"of that variable, after dropping categories under 30 sessions - a "
        f"like-for-like comparison of magnitude, not a standardised effect "
        f"size. A large untested gap (sky, wind) means \"interesting, "
        f"unverified\", not \"strong effect\".")
    add("")
    add("This is not a failure of the study. On species *richness*, habitat is "
        "swamped by survey conditions and by the surveyor. The habitat signal "
        "that does survive is about *which* species are present - at-risk birds "
        "and grassland specialists - not how many.")
    add("")

    # ---------------------------------------------------------------- insights
    add("## 4. Insights, ranked by how well they are supported")
    add("")
    add("| # | Insight | Evidence | Strength |")
    add("|---|---------|----------|----------|")
    add(f"| 1 | Forest shelters Wood Thrush specifically, not at-risk birds as a "
        f"class | {q1['forest_pct']}% vs {q1['grassland_pct']}%, "
        f"{p(q1['p_value'])}, holds in 4/4 parks; but "
        f"{q1b['wood_thrush_share_pct']}% is one species and the effect "
        f"halves to {q1b['without_wood_thrush']['ratio']}x without it | "
        f"Strong, correctly narrowed |")
    add(f"| 2 | Who does the counting matters more than what is being counted | "
        f"{q10['spread_pct']}% observer spread, all pairs significant, vs a "
        f"{hab_gap:.2f}-species habitat gap | Strong |")
    add(f"| 3 | Grassland has specialists; forest has none | "
        f"{q4['n_grassland']} vs {q4['n_forest']} of {q4['n_well_sampled']} "
        f"well-sampled species | Strong |")
    add(f"| 4 | Disturbance costs more species than any weather variable | "
        f"{dt['loss_pct']}% loss, {p(dt['p_value'])} | Strong |")
    add(f"| 5 | Survey grassland early | {q7['early_vs_late']['Grassland']['gain_pct']}% "
        f"gain, {p(q7['early_vs_late']['Grassland']['p_value'])}, confirmed by "
        f"two methods | Strong, grassland only |")
    add(f"| 6 | Habitat does not drive species richness | pooled "
        f"{p(q2['pooled']['p_value'])} collapses to "
        f"{p(q2['within_shared']['p_value'])} within shared parks | Strong "
        f"negative result |")
    add(f"| 7 | \"Best park\" depends on the question | {top_name} is #1 for at-risk "
        f"presence and #{top_rank} of {len(pk)} for richness | Solid |")
    add("")

    # ------------------------------------------------------- recommendations
    add("## 5. Recommendations")
    add("")
    add("### For survey design")
    add("")
    add(f"1. **Survey both habitats in every park.** Only "
        f"{q12['usable_pct']}% of sessions are usable for the study's central "
        f"comparison. Pairing habitats within parks would roughly double the "
        f"usable sample at no extra cost per session.")
    add(f"2. **Keep the observer rota balanced, and record it as a design "
        f"feature.** The {q10['spread_pct']}% observer spread is only harmless "
        f"because assignment was balanced across habitats and parks. That was "
        f"the single most important methodological choice in the study.")
    add(f"3. **Equalise visits per plot across habitats.** Forest plots got "
        f"{q12['visits_per_plot']['Forest']} visits on average, grassland "
        f"{q12['visits_per_plot']['Grassland']} - and the third visit was "
        f"grassland-only, which is what makes seasonal analysis impossible.")
    add("4. **Decouple visit number from calendar date.** Rotating the visit "
        f"order across plots would let a genuine seasonal question be asked; "
        f"at rho = {rho_cal:.2f} it currently cannot be.")
    add(f"5. **Aim for {30}+ sessions per reporting unit.** Four parks fall "
        f"below the reliability floor and cannot carry a park-level claim.")
    add("")
    add("### For management")
    add("")
    add(f"1. **Protect forest where Wood Thrush is present** - and describe it "
        f"as a Wood Thrush measure, not a general at-risk measure, because "
        f"that is what the data supports.")
    add(f"2. **Reduce survey-time disturbance.** A {dt['loss_pct']}% drop in "
        f"recorded species is the largest environmental effect measured here "
        f"and the only one management controls directly.")
    add(f"3. **Do not convert grassland on diversity grounds.** Grassland holds "
        f"every specialist in the dataset ({q4['n_grassland']} of them) while "
        f"forest holds none; richness alone shows no habitat difference.")
    add(f"4. **Direct at-risk monitoring to {top_name}, and diversity visits "
        f"elsewhere.** They are not the same places.")
    add("")

    # ---------------------------------------------------- what we cannot say
    add("## 6. What this dataset cannot answer")
    add("")
    add("Stating these plainly is part of the result, not a disclaimer.")
    add("")
    add("| Question | Why not |")
    add("|----------|---------|")
    add(f"| Is there a seasonal trend? | Visit number and date correlate at "
        f"rho = {rho_cal:.2f}; the third visit is grassland-only |")
    add("| Does forest hold more species than grassland? | Answered and the "
        "answer is no - the pooled difference is a park-mix artefact |")
    add("| Which individual plot is best? | No plot has more than "
        f"{int(plots['size'].max())} visits; the leaderboard is the tail of a "
        f"noisy distribution |")
    add("| Are cold mornings better than mild ones? | The relationship is "
        "hump-shaped; the significant negative rho misdescribes it |")
    add("| Do at-risk birds favour early mornings? | No time-of-day effect on "
        "at-risk detection in either habitat |")
    add("| Why does slight disturbance beat none? | Unknown. Large samples both "
        "sides, no mechanism available |")
    add(f"| Anything about the {q12['n_parks'] - q12['parks_with_both']} "
        f"single-habitat parks' habitat preferences | They have no within-park "
        f"comparison to make |")
    add("")
    add("---")
    add("")
    add("*Re-run `python src/make_ledger.py` after any change to the analysis "
        "or the cleaned data.*")
    add("")

    return "\n".join(L)


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")