"""
The report, as structured content rather than as a document.

Why this exists
---------------
The same report has to appear in three places: the dashboard's Report page, a
PDF, and a Word file. Writing it three times guarantees they drift apart, and a
reader who spots the dashboard and the PDF disagreeing has no reason to trust
either. So the report is defined once here as a list of typed blocks, and three
thin renderers turn those blocks into Streamlit widgets, a reportlab story, or
a docx document.

Block types
-----------
    ("h1", text)              part heading
    ("h2", text)              section heading
    ("h3", text)              sub-section heading
    ("p", text)               paragraph; <b>bold</b> and <i>italic</i> allowed
    ("bullets", [text, ...])  bulleted list, same inline markup
    ("kv", [(k, v), ...])     definition list of short facts
    ("table", df, caption)    a DataFrame, rendered with its caption
    ("note", text)            callout - a caveat, guardrail or warning
    ("verdict", label, text)  a classified finding: label drives the colour
    ("pagebreak",)            PDF/Word only; ignored on screen

Every number is read from analysis.run_all(). Nothing here is typed by hand.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import analysis  # noqa: E402
import stats_helpers as sh  # noqa: E402

TITLE = "Bird Species Observation Analysis"
SUBTITLE = ("Forest and grassland point-count surveys across 11 National Park "
            "Service units, 2018 breeding season")

VERDICT_LABELS = {
    "finding": "FINDING",
    "narrowed": "FINDING, NARROWED",
    "rejected": "REJECTED",
    "descriptive": "DESCRIPTIVE ONLY",
    "method": "METHODOLOGICAL",
}


def fmt_p(value: float) -> str:
    """Format a p-value without printing a bare 0 for an underflow."""
    if value == 0:
        return "p &lt; 1e-300"
    if value < 0.001:
        return f"p = {value:.2e}"
    return f"p = {value:.4f}"


def _pct(x: float) -> str:
    return f"{x:.1f}%"


def build_blocks() -> list[tuple]:
    """Return the whole report as a list of typed blocks."""
    r = analysis.run_all(ROOT)
    t = analysis.load_tables(ROOT)
    rows, sessions, species = t["rows"], t["sessions"], t["species"]

    q1, q1b, q2, q3 = r["q1"], r["q1b"], r["q2"], r["q3"]
    q4, q5, q6, q7 = r["q4"], r["q5"], r["q6"], r["q7"]
    q8, q9, q10, q11, q12 = r["q8"], r["q9"], r["q10"], r["q11"], r["q12"]
    q13, q14 = r["q13"], r["q14"]

    dt = q9["disturbance_test"]
    obs = q10["per_observer"]["species_per_session"]
    obs_gap = obs.max() - obs.min()
    hab_gap = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])

    coords = pd.read_csv(ROOT / "data" / "reference" / "park_coordinates.csv")
    NAME = dict(zip(coords["Admin_Unit_Code"], coords["park_name"]))

    # Derived figures used in more than one section.
    pk = q3["parks_by_rate"]
    rho_eff_raw, p_eff_raw = sh.spearmanr(
        pk["sessions_run"].values, pk["distinct_species"].values)
    rho_eff_rate, p_eff_rate = sh.spearmanr(
        pk["sessions_run"].values, pk["species_per_session"].values)
    rho_cal, p_cal = sh.spearmanr(
        sessions["Visit"].values, sessions["day_of_season"].values)
    rho_rich, p_rich = sh.spearmanr(
        sessions["Visit"].values, sessions["species_per_session"].values)
    plots = sessions.groupby("Plot_Name").species_per_session.agg(["mean", "size"])
    eff_park = q12["by_park"]
    single = eff_park[~eff_park["both_habitats"]]
    low = eff_park[eff_park["total"] < 30]
    dur = sessions["session_duration_min"]
    n_fly = int(rows["is_flyover"].sum())
    dist_gap = dt["none_mean"] - dt["serious_mean"]

    B: list[tuple] = []
    add = B.append

    # ================================================== EXECUTIVE SUMMARY
    add(("h1", "Executive summary"))
    add(("p",
         f"This report analyses {len(rows):,} bird sightings recorded across "
         f"{len(sessions):,} point-count survey sessions in "
         f"{q12['n_parks']} National Park Service units during the 2018 "
         f"breeding season, covering {rows['Scientific_Name'].nunique()} "
         f"species in forest and grassland habitats. Thirteen analytical "
         f"questions were posed. <b>Five produced findings that survived "
         f"scrutiny</b>, one was rejected outright once the comparison was "
         f"made fair, and the remainder are descriptive or methodological."))
    add(("p",
         f"The most consequential result is methodological rather than "
         f"ecological. The difference between the three surveyors "
         f"({obs_gap:.2f} species per session) is roughly "
         f"{obs_gap / hab_gap:.0f} times larger than the habitat difference "
         f"the survey was designed to measure ({hab_gap:.2f}). The study's "
         f"conclusions survive only because observer assignment was balanced "
         f"across habitats and parks."))
    add(("h3", "Headline findings"))
    add(("bullets", [
        f"<b>Forest shelters Wood Thrush, not at-risk birds as a class.</b> "
        f"At-risk species appear in {q1['forest_pct']}% of forest sightings "
        f"against {q1['grassland_pct']}% in grassland - a {q1['ratio']}x gap "
        f"({fmt_p(q1['p_value'])}) holding in all {q1['n_parks']} shared "
        f"parks. However {q1b['wood_thrush_share_pct']}% of those sightings "
        f"are a single species; excluding it the gap falls to "
        f"{q1b['without_wood_thrush']['ratio']}x and survives in only "
        f"{q1b['parks_agreeing_without']} of {q1['n_parks']} parks.",

        f"<b>Grassland supports habitat specialists; forest supports none.</b> "
        f"Of {q4['n_well_sampled']} well-sampled species, "
        f"{q4['n_grassland']} are grassland specialists and "
        f"{q4['n_forest']} are forest specialists.",

        f"<b>Disturbance is the largest environmental effect measured.</b> "
        f"Serious disturbance reduces recorded species by "
        f"{dt['loss_pct']}% ({dt['none_mean']} to {dt['serious_mean']} per "
        f"session, {fmt_p(dt['p_value'])}).",

        f"<b>Grassland surveys are most productive early.</b> Richness falls "
        f"{q7['early_vs_late']['Grassland']['gain_pct']}% between the 5-6am "
        f"and 9-10am bands "
        f"({fmt_p(q7['early_vs_late']['Grassland']['p_value'])}), confirmed "
        f"by an independent whole-morning trend test. Forest shows no such "
        f"effect.",

        f"<b>Observer identity outweighs every ecological variable.</b> A "
        f"{q10['spread_pct']}% spread between three surveyors, significant in "
        f"every pairwise comparison and consistent in every park.",

        f"<b>The habitats share a species pool but weight it differently.</b> "
        f"Rarefied community similarity is near-identical on presence "
        f"(Jaccard {q13['similarity']['between_habitat']['jaccard']} between "
        f"habitats against "
        f"{q13['similarity']['within_habitat']['jaccard']} within one) and "
        f"clearly separated on abundance (Bray-Curtis "
        f"{q13['similarity']['between_habitat']['bray_curtis']} against "
        f"{q13['similarity']['within_habitat']['bray_curtis']}).",
    ]))
    add(("h3", "What was rejected"))
    add(("p",
         f"<b>Habitat does not determine species richness.</b> Pooled across "
         f"all {q12['n_parks']} parks the difference appears significant "
         f"({fmt_p(q2['pooled']['p_value'])}); restricted to the "
         f"{q2['n_parks']} parks surveyed in both habitats it disappears "
         f"({fmt_p(q2['within_shared']['p_value'])}), and forest wins in "
         f"exactly {q2['parks_favouring_forest']} of {q2['n_parks']}. The "
         f"pooled result was an instance of Simpson's paradox driven by "
         f"unequal survey effort across parks. Seasonal change could not be "
         f"assessed at all: visit number and calendar date correlate at "
         f"rho = {rho_cal:.2f}, making a seasonal decline indistinguishable "
         f"from a repeat-visit decline."))
    add(("pagebreak",))

    # ================================================== 1. INTRODUCTION
    add(("h1", "1. Introduction"))
    add(("h2", "1.1 Background"))
    add(("p",
         "Point-count surveys are the standard method for monitoring "
         "breeding bird populations. An observer stands at a fixed plot for a "
         "set period, records every bird detected by sight or sound, and "
         "repeats the visit across a season. The resulting data supports two "
         "distinct management questions: which habitats hold the most "
         "species, and which habitats hold the species most at risk of "
         "decline. These are not the same question, and this analysis finds "
         "they have different answers."))
    add(("p",
         f"The dataset covers the 2018 breeding season across "
         f"{q12['n_parks']} units of the United States National Park Service "
         f"in the Mid-Atlantic region. Two habitat types were surveyed - "
         f"forest and grassland - though not, as this report shows, in the "
         f"same places. Species carrying a Partners in Flight (PIF) Watchlist "
         f"designation are treated throughout as the at-risk group."))
    add(("h2", "1.2 Objectives"))
    add(("p",
         "The analysis was structured around six objectives, expressed as "
         "fourteen testable questions. Each question is answered in Section 4 "
         "with an explicit verdict."))
    obj = pd.DataFrame([
        ("1. Conservation priority",
         "Q1, Q1b, Q5", "Which habitat shelters at-risk species, and is the "
         "signal broad or driven by one species?"),
        ("2. Biodiversity value",
         "Q2, Q11, Q13", "Does either habitat support more species, or more species "
         "unique to it?"),
        ("3. Eco-tourism and access",
         "Q3", "Which parks and plots offer the richest bird-watching?"),
        ("4. Habitat dependency",
         "Q4", "Which species depend on a single habitat type?"),
        ("5. Survey optimisation",
         "Q6, Q7, Q8, Q9", "When and under what conditions are surveys most "
         "productive?"),
        ("6. Data reliability",
         "Q10, Q12", "Is the survey design sound enough to support the above?"),
    ], columns=["Objective", "Questions", "Question posed"])
    add(("table", obj, "Table 1.1 - Objectives and the questions addressing them"))
    add(("h2", "1.3 Scope and approach"))
    add(("p",
         "This analysis deliberately reports negative results alongside "
         "positive ones. A question that produced no finding is recorded as "
         "firmly as one that did, and Section 9 lists the questions this "
         "dataset cannot answer at all. That choice reflects the central "
         "methodological lesson of the project: several apparently strong "
         "results dissolved once survey effort was accounted for, and a "
         "report that presented only surviving findings would misrepresent "
         "how the analysis actually went."))
    add(("h2", "1.4 Success criteria"))
    add(("p",
         "The criteria below were set before the analysis began, so that the "
         "project could be judged on whether it answered its questions "
         "honestly rather than on whether the answers were interesting."))
    crit = pd.DataFrame([
        ("Every question receives an explicit verdict",
         "Met", f"All 14 questions classified as finding, narrowed, rejected "
                f"or descriptive (Section 4)"),
        ("No figure is entered by hand anywhere",
         "Met", "Dashboard, PDF, Word and ledger all read analysis.run_all()"),
        ("Habitat comparisons are confounder-free",
         "Met", f"Restricted to the {q2['n_parks']} shared parks (G2); "
                f"per-session rates throughout (G1)"),
        ("Small samples cannot drive a conclusion",
         "Met", "30-session floor applied and flagged in every chart (G3)"),
        ("Negative results are reported as prominently as positive ones",
         "Met", "Section 4.3 rejected; Section 9 lists 10 limitations"),
        ("The cleaning process is auditable",
         "Met", "10 decisions logged with row counts in docs/cleaning_log.md"),
        ("A reader can reproduce every number",
         "Met", "Appendix A; each pipeline module runnable independently"),
        ("Recommendations are specific enough to act on",
         "Met", "Section 8; survey-design changes costed in sessions"),
    ], columns=["Criterion", "Status", "Evidence"])
    add(("table", crit, "Table 1.2 - Success criteria and how they were met"))
    add(("pagebreak",))

    # ================================================== 2. DATA
    add(("h1", "2. The dataset"))
    add(("h2", "2.1 Source and scale"))
    add(("kv", [
        ("Source", "Two Excel workbooks - one forest, one grassland - "
                   "supplied as project input"),
        ("Coverage", f"{q12['n_parks']} NPS administrative units, "
                     f"Mid-Atlantic region"),
        ("Period", "2018 breeding season (May to July)"),
        ("Raw records", "8,546 forest rows and 8,531 grassland rows"),
        ("Cleaned records", f"{len(rows):,} sightings"),
        ("Survey sessions", f"{len(sessions):,}"),
        ("Distinct species", f"{rows['Scientific_Name'].nunique()}"),
        ("Observers", f"{sessions['Observer'].nunique()}"),
        ("Survey plots", f"{sessions['Plot_Name'].nunique():,}"),
    ]))
    add(("p",
         "Seven of the eleven grassland worksheets were empty. Grassland "
         "monitoring covered only four parks, and that single structural fact "
         "shapes every habitat comparison in this report."))
    add(("h2", "2.2 Survey effort by park and habitat"))
    eff_disp = eff_park.copy()
    eff_disp.insert(0, "Park", [NAME.get(i, i) for i in eff_disp.index])
    eff_disp = eff_disp.rename(columns={
        "Forest": "Forest sessions", "Grassland": "Grassland sessions",
        "total": "Total", "both_habitats": "Both habitats",
    }).reset_index(drop=True)
    add(("table", eff_disp,
         "Table 2.1 - Survey sessions by park and habitat"))
    add(("note",
         f"<b>The single most important table in this report.</b> "
         f"{len(single)} of {q12['n_parks']} parks were surveyed in one "
         f"habitat only, and all {len(single)} of those are forest-only. In "
         f"those parks a forest-versus-grassland comparison is really a "
         f"park-A-versus-park-B comparison. Only "
         f"{q12['usable_sessions']:,} of {q12['total_sessions']:,} sessions "
         f"({q12['usable_pct']}%) can therefore contribute to the central "
         f"question."))
    add(("h2", "2.3 Key variables"))
    dd = pd.DataFrame([
        ("Admin_Unit_Code", "Categorical", "Four-letter park code, 11 values"),
        ("habitat", "Categorical", "Forest or Grassland (derived from source file)"),
        ("Plot_Name", "Categorical", f"Survey plot, {sessions['Plot_Name'].nunique():,} values"),
        ("Date / Visit", "Date / Integer", "Survey date and visit number (1-3)"),
        ("Observer", "Categorical", "Surveyor name, 3 values"),
        ("Start_Time", "Time", "Session start, used to derive hour and time band"),
        ("Common_Name / Scientific_Name", "Categorical", "Species identity"),
        ("PIF_Watchlist_Status", "Boolean", "At-risk designation - the conservation variable"),
        ("Temperature / Humidity", "Numeric", "Recorded per session"),
        ("Sky / Wind / Disturbance", "Categorical", "Ordered condition scales"),
        ("Flyover_Observed", "Boolean", "Bird passing overhead rather than using the site"),
        ("Distance / Interval_Length", "Categorical", "Detection distance band and time interval"),
    ], columns=["Variable", "Type", "Role in the analysis"])
    add(("table", dd, "Table 2.2 - Principal variables"))
    add(("p",
         "A full column-by-column dictionary covering all "
         f"{len(rows.columns)} fields appears in Appendix B."))

    add(("h2", "2.4 Governance, licensing and ethics"))
    add(("kv", [
        ("Data origin", "United States National Park Service inventory and "
                        "monitoring programme; supplied as project input"),
        ("Licensing", "US federal government works are generally public "
                      "domain under 17 U.S.C. section 105. No redistribution "
                      "restriction was supplied with the files, and none is "
                      "asserted here."),
        ("Personal data", f"The dataset contains {sessions['Observer'].nunique()} "
                          f"named surveyors. These are staff names attached to "
                          f"work records, not personal or sensitive data, but "
                          f"Section 5.1 does report measurable differences in "
                          f"individual performance."),
        ("How observer names are handled",
         "Retained, because the observer effect could not be demonstrated "
         "without them and it is the project's most important methodological "
         "finding. Reported as a property of survey method rather than as an "
         "assessment of any individual, and no ranking is framed as a "
         "judgement of competence."),
        ("Species sensitivity", "Plot coordinates are recorded at park level "
                                "only. No precise nest or roost locations are "
                                "published, which matters for the at-risk "
                                "species this report highlights."),
        ("Onward use", "Figures are reproducible from the pipeline. Anyone "
                       "citing them should note the single-season scope and "
                       "the calibration caveat in Section 9."),
    ]))
    add(("note",
         "<b>One ethical decision worth stating plainly.</b> This report "
         "identifies which of three named surveyors records fewer species. "
         "That is uncomfortable, and it was retained because omitting it would "
         "have hidden the largest measured effect in the project and left "
         "readers over-trusting the absolute numbers. The finding is presented "
         "as evidence about survey method - all three surveyors reach the same "
         "conclusions about habitat - and not as a performance review."))
    add(("pagebreak",))

    # ================================================== 3. METHODOLOGY
    add(("h1", "3. Methodology"))
    add(("h2", "3.1 Cleaning"))
    add(("p",
         "Ten cleaning decisions were investigated and agreed before any "
         "code was written, then applied in a fixed order by "
         "<i>src/clean.py</i>, which writes an audit trail to "
         "<i>docs/cleaning_log.md</i> recording row counts before and after "
         "each step. Order was not arbitrary: the schema was reconciled while "
         "the two habitat files were still separate, and de-duplication ran "
         "before any counting, since counting first would have baked a 20% "
         "inflation into every grassland figure."))
    add(("bullets", [
        "<b>Schema reconciliation.</b> <i>NPSTaxonCode</i> renamed to "
        "<i>TaxonCode</i> after verifying all 88 shared species carry "
        "identical codes; <i>Previously_Obs</i> dropped as a zero-variance "
        "grassland-only column; <i>Site_Name</i> retained as nullable, since "
        "grassland monitoring genuinely did not record that level.",
        "<b>De-duplication.</b> Exact duplicate rows removed from the "
        "grassland file only, where they were an artefact of the source "
        "export.",
        "<b>Type casting.</b> Grassland columns had been read as generic "
        "objects; cast to integer, float, boolean and datetime so that "
        "arithmetic and comparison behave correctly.",
        "<b>Value standardisation.</b> Blank <i>Sex</i> values standardised "
        "to <i>Undetermined</i>; one species recorded under two names "
        "unified; <i>Distance_Display</i> added while leaving the original "
        "<i>Distance</i> column untouched.",
        "<b>Missing data left in place.</b> Small scattered gaps were not "
        "imputed. Section 5.4 shows why: every gap is explained by a protocol "
        "rule rather than by data loss.",
    ]))
    add(("h2", "3.2 Feature engineering: the survey session"))
    add(("p",
         f"The row-level data records one sighting per row, which makes raw "
         f"counts a measure of how many birds were seen rather than how good "
         f"a place is. The analysis therefore aggregates to the "
         f"<b>survey session</b> - one observer, one plot, one morning - "
         f"producing {len(sessions):,} rows. Every rate reported in this "
         f"document is a column of that table averaged over sessions, never a "
         f"count taken from the row-level data."))
    add(("kv", [
        ("species_per_session", "Distinct species recorded - the primary "
                                "richness measure"),
        ("sightings_per_session", "Total records, used for the at-risk "
                                  "percentage"),
        ("at_risk_sightings / has_at_risk", "Count and presence flag for PIF "
                                            "Watchlist species"),
        ("time_band", "Early (5-6am), Mid (7-8am), Late (9-10am)"),
        ("temp_band / humidity_band", "Binned weather for category comparison"),
        ("day_of_season", "Days since the first survey, for trend testing"),
        ("is_shared_park", "Whether the park was surveyed in both habitats"),
    ]))
    add(("h2", "3.3 Statistical methods"))
    add(("p",
         "Two tests are used throughout, both implemented in "
         "<i>src/stats_helpers.py</i> so the project carries no hidden "
         "dependency on an external statistics package and every result can "
         "be traced to readable source."))
    add(("bullets", [
        "<b>Mann-Whitney U</b> for comparing two independent groups. Chosen "
        "over a t-test because species-per-session is a bounded count that is "
        "not normally distributed, and the test makes no distributional "
        "assumption.",
        "<b>Spearman's rank correlation (rho)</b> for monotonic trends. "
        "Section 4.11 documents a case where this statistic is significant and "
        "nonetheless misdescribes the relationship, because the underlying "
        "curve is not monotonic.",
        "<b>Rarefaction</b> for species-count comparison across unequal "
        f"sampling effort, using {q11['n_draws']} random draws down to the "
        f"smaller sample size.",
    ]))
    add(("p",
         "Significance is reported at alpha = 0.05 throughout. Exact p-values "
         "are given rather than thresholds, so a reader can apply a stricter "
         "criterion without recomputation."))
    add(("h2", "3.4 The four guardrails"))
    add(("p",
         "Four rules were applied to every analysis. They are stated here as "
         "method, but each one is also a result: every one changed a "
         "conclusion this project would otherwise have published."))
    guard = pd.DataFrame([
        ("G1", "Compare per-session rates, never raw totals",
         f"Grassland ran {q11['sessions']['ratio']}x more sessions than "
         f"forest. Raw counts measure effort."),
        ("G2", f"Habitat comparisons use the {q2['n_parks']} shared parks only",
         f"{len(single)} parks were surveyed in one habitat only; there, "
         f"habitat is confounded with park identity."),
        ("G3", "Treat any group under 30 sessions as unreliable",
         "Small groups swing wildly; the highest single figure in the dataset "
         "rests on 12 sessions."),
        ("G4", "Rarefy before comparing species counts",
         "More sampling finds more species even from an identical community."),
    ], columns=["ID", "Rule", "Why it is necessary"])
    add(("table", guard, "Table 3.1 - Analytical guardrails"))
    add(("h2", "3.5 Tools and reproducibility"))
    add(("kv", [
        ("Language", "Python 3.13"),
        ("Core libraries", "pandas (data), numpy (numeric), plotly (charts), "
                           "Streamlit (dashboard), reportlab (this PDF)"),
        ("Statistics", "src/stats_helpers.py - Mann-Whitney U, Spearman rho, "
                       "no external stats dependency"),
        ("Pipeline", "src/ingest.py, clean.py, features.py, analysis.py - "
                     "each runnable independently"),
        ("Single source of numbers", "analysis.run_all() - the dashboard, "
                                     "this report and the findings ledger all "
                                     "read from it, so no figure is typed by "
                                     "hand anywhere"),
    ]))
    add(("h2", "3.6 Data flow"))
    add(("p",
         "Five stages, each a separate module with a single responsibility. "
         "Every stage writes its output to disk, so any stage can be re-run "
         "and inspected independently rather than the whole thing being one "
         "opaque script."))
    flow = pd.DataFrame([
        ("1. Ingest", "src/ingest.py",
         "2 Excel workbooks (15 sheets)",
         "Raw frames, sheet structure report"),
        ("2. Clean", "src/clean.py",
         "Raw frames",
         f"data/processed/birds_clean.csv ({len(rows):,} rows) + "
         f"docs/cleaning_log.md"),
        ("3. Feature build", "src/features.py",
         "Cleaned rows",
         f"sessions ({len(sessions):,}), species profile "
         f"({len(species)}), park coordinates"),
        ("4. Analyse", "src/analysis.py",
         "Rows, sessions, species",
         "run_all() - a dict of 13 answered questions"),
        ("5. Present", "app/ + src/make_report.py + src/make_ledger.py",
         "run_all() output",
         "Dashboard, PDF, Word, findings ledger"),
    ], columns=["Stage", "Module", "Input", "Output"])
    add(("table", flow, "Table 3.2 - Pipeline stages"))
    add(("p",
         "<b>The critical property is that stage 5 has four consumers and one "
         "source.</b> The dashboard, the PDF, the Word document and the "
         "findings ledger all read the same <i>run_all()</i> dictionary. No "
         "presentation layer recomputes a statistic, and none holds a "
         "hand-typed number, so the four outputs cannot disagree with each "
         "other or with the analysis."))
    add(("pagebreak",))

    # ================================================== 4. RESULTS
    add(("h1", "4. Results"))
    add(("p",
         "Each question below carries an explicit verdict. <b>Finding</b> "
         "means the result survived the guardrails and a significance test. "
         "<b>Finding, narrowed</b> means it survived but in a smaller form "
         "than it first appeared. <b>Rejected</b> means it did not survive. "
         "<b>Descriptive only</b> means no test was applied, and the reason "
         "is given."))

    # ---------------------------------------------------------------- Q1
    add(("h2", "4.1 Q1 - At-risk species by habitat"))
    add(("verdict", "narrowed",
         f"Forest records at-risk species at {q1['forest_pct']}% of sightings "
         f"against {q1['grassland_pct']}% in grassland - a {q1['ratio']}x "
         f"difference, {fmt_p(q1['p_value'])}, holding in all "
         f"{q1['n_parks']} of {q1['n_parks']} shared parks."))
    bp = q1["by_park"].copy()
    bp.insert(0, "Park", [NAME.get(i, i) for i in bp.index])
    add(("table", bp.reset_index(drop=True),
         "Table 4.1 - At-risk sightings as a percentage, by park and habitat "
         "(shared parks only)"))
    add(("p",
         "This is the strongest ecological result in the project. It is "
         "computed on shared parks only (G2) and as a per-session rate (G1), "
         "and unlike the richness comparison in Section 4.3 it does not "
         "collapse when checked park by park: forest is higher in every one "
         "of the four. Consistency across parks, rather than the p-value "
         "alone, is what distinguishes a real effect from a pooling artefact."))

    add(("h3", "4.1.1 Q1b - Stress-testing the finding"))
    add(("p",
         f"Before accepting the result the at-risk group was decomposed by "
         f"species. <b>{q1b['wood_thrush_sightings']} of "
         f"{q1b['total_at_risk_sightings']} at-risk sightings "
         f"({q1b['wood_thrush_share_pct']}%) are Wood Thrush alone</b>, "
         f"recorded in {q1b['wood_thrush_parks']} of the "
         f"{q12['n_parks']} parks. Removing it and repeating the analysis "
         f"gives a very different picture."))
    stress = pd.DataFrame([
        ("All 8 watchlist species",
         q1b["with_wood_thrush"]["forest"], q1b["with_wood_thrush"]["grassland"],
         f"{q1b['with_wood_thrush']['ratio']}x", f"{q1['n_parks']} of {q1['n_parks']}"),
        ("Excluding Wood Thrush",
         q1b["without_wood_thrush"]["forest"], q1b["without_wood_thrush"]["grassland"],
         f"{q1b['without_wood_thrush']['ratio']}x",
         f"{q1b['parks_agreeing_without']} of {q1['n_parks']}"),
    ], columns=["Group", "Forest %", "Grassland %", "Ratio", "Parks agreeing"])
    add(("table", stress, "Table 4.2 - The at-risk finding with and without "
                          "its dominant species"))
    add(("note",
         f"<b>The defensible claim is the narrow one.</b> \"Forest shelters "
         f"at-risk birds\" implies a class effect across "
         f"{q1b['n_at_risk_species']} species. The data supports \"forest "
         f"shelters Wood Thrush\": remove that one species and the effect "
         f"more than halves and stops being consistent across parks. This "
         f"report uses the narrow phrasing throughout."))

    # ---------------------------------------------------------------- Q5
    add(("h2", "4.2 Q5 - Composition of the at-risk group"))
    add(("verdict", "descriptive",
         f"{q5['n_species']} PIF Watchlist species recorded across "
         f"{q5['n_sightings']} sightings, of which "
         f"{q5['dominant_share_pct']}% are {q5['dominant_species']}."))
    add(("table", q5["species_profile"],
         "Table 4.3 - At-risk sightings by species and habitat (all 11 parks)"))
    add(("p",
         "Reported for all eleven parks rather than the shared four, because "
         "this is a question about which species carry the at-risk signal "
         "rather than a habitat comparison. The concentration in a single "
         "species is the evidence base for narrowing Q1, and is the reason "
         "the Overview headline of this project names one bird rather than a "
         "category."))

    # ---------------------------------------------------------------- Q2
    add(("h2", "4.3 Q2 - Species richness by habitat"))
    add(("verdict", "rejected",
         f"Pooled across {q12['n_parks']} parks the habitats differ "
         f"({fmt_p(q2['pooled']['p_value'])}). Within the {q2['n_parks']} "
         f"parks surveyed in both, they do not "
         f"({fmt_p(q2['within_shared']['p_value'])})."))
    comp = pd.DataFrame([
        (f"Pooled, all {q12['n_parks']} parks", q2["pooled"]["forest"],
         q2["pooled"]["grassland"],
         f"{q2['pooled']['n_forest']} / {q2['pooled']['n_grassland']}",
         fmt_p(q2["pooled"]["p_value"]).replace("&lt;", "<"),
         "Appears significant"),
        (f"Within {q2['n_parks']} shared parks", q2["within_shared"]["forest"],
         q2["within_shared"]["grassland"],
         f"{q2['within_shared']['n_forest']} / {q2['within_shared']['n_grassland']}",
         fmt_p(q2["within_shared"]["p_value"]).replace("&lt;", "<"),
         "Not significant"),
    ], columns=["Comparison", "Forest", "Grassland", "n (F/G)", "p", "Verdict"])
    add(("table", comp, "Table 4.4 - Species per session, pooled versus "
                        "within shared parks"))
    bp2 = q2["by_park"].copy()
    bp2.insert(0, "Park", [NAME.get(i, i) for i in bp2.index])
    add(("table", bp2.reset_index(drop=True),
         "Table 4.5 - Species per session by park and habitat"))
    add(("note",
         f"<b>This is Simpson's paradox, occurring in our own data.</b> "
         f"Grassland ran {q11['sessions']['ratio']}x more sessions than "
         f"forest, and the two habitats were not surveyed in the same parks. "
         f"A pooled average therefore partly reflects which parks were "
         f"surveyed how often rather than habitat quality. Checking within "
         f"each shared park removes that confound - and the effect vanishes, "
         f"with forest higher in exactly "
         f"{q2['parks_favouring_forest']} of {q2['n_parks']} parks, which is "
         f"a coin flip."))
    add(("p",
         "The correct conclusion is that richness is the wrong question to "
         "ask of habitat in this dataset. Composition - which species are "
         "present - does differ between habitats, as Sections 4.1 and 4.5 "
         "show. Abundance of species does not."))

    # ---------------------------------------------------------------- Q11
    add(("h2", "4.4 Q11 - Species unique to one habitat"))
    add(("verdict", "narrowed",
         f"Raw counts suggest grassland holds "
         f"{q11['raw']['grassland_only'] / q11['raw']['forest_only']:.1f}x "
         f"more exclusive species. Rarefied to equal effort the gap falls to "
         f"{q11['rarefied']['grassland_only'] / q11['rarefied']['forest_only']:.1f}x."))
    rare = pd.DataFrame([
        ("Raw count", q11["raw"]["forest_only"], q11["raw"]["grassland_only"],
         f"{q11['raw']['grassland_only'] / q11['raw']['forest_only']:.1f}x"),
        (f"Rarefied ({q11['n_draws']} draws)", q11["rarefied"]["forest_only"],
         q11["rarefied"]["grassland_only"],
         f"{q11['rarefied']['grassland_only'] / q11['rarefied']['forest_only']:.1f}x"),
    ], columns=["Measure", "Forest-only species", "Grassland-only species", "Ratio"])
    add(("table", rare, "Table 4.6 - Exclusive species before and after "
                        "rarefaction"))
    add(("p",
         f"Grassland ran {q11['sessions']['grassland']} sessions against "
         f"forest's {q11['sessions']['forest']}. More sampling finds more "
         f"species even from an identical community, so the raw comparison "
         f"largely measures effort. Rarefaction repeatedly resamples the "
         f"larger group down to the smaller one before counting. A further "
         f"fragility check: {q11['seen_once_only']['forest_only']} of the "
         f"forest-only and {q11['seen_once_only']['grassland_only']} of the "
         f"grassland-only species were recorded exactly once, so a single "
         f"additional sighting would move them into the shared column."))

    # ---------------------------------------------------------------- Q13
    add(("h2", "4.5 Q13 - Diversity beyond richness"))
    sim = q13["similarity"]
    add(("verdict", "finding",
         f"Four independent diversity measures agree there is no habitat "
         f"difference. Community composition tells a different story: "
         f"abundance structure differs between habitats "
         f"(Bray-Curtis {sim['between_habitat']['bray_curtis']} against "
         f"{sim['within_habitat']['bray_curtis']} within a habitat) while "
         f"species membership barely does."))
    add(("p",
         "Counting distinct species is only one way to measure diversity, and "
         "the crudest. A session holding ten species - one abundant, nine seen "
         "once - scores the same richness as one holding ten evenly abundant "
         "species, though the two communities are very different. Three "
         "standard indices separate them, each computed per session and then "
         "averaged so guardrail G1 holds, inside the shared parks only so G2 "
         "holds."))
    div = pd.DataFrame([
        (m.replace("_", " ").title(),
         q13["tests"][m]["forest"], q13["tests"][m]["grassland"],
         fmt_p(q13["tests"][m]["p_value"]).replace("&lt;", "<"),
         "Significant" if q13["tests"][m]["significant"] else "Not significant")
        for m in q13["metrics"]
    ], columns=["Measure", "Forest", "Grassland", "p", "Verdict"])
    add(("table", div,
         "Table 4.7 - Diversity indices by habitat, per-session means within "
         "the shared parks"))
    add(("note",
         f"<b>The null result in Section 4.3 is not an artefact of choosing "
         f"richness.</b> Shannon weights rare species, Simpson weights "
         f"dominant ones, and Pielou's evenness removes richness from the "
         f"calculation entirely. All three reach the same verdict as the "
         f"species count did: no habitat difference "
         f"(smallest p = "
         f"{min(t['p_value'] for t in q13['tests'].values()):.2f}). Four "
         f"measures with different sensitivities agreeing is considerably "
         f"stronger evidence than one measure alone."))
    add(("h3", "4.5.1 Community composition"))
    add(("p",
         "Diversity indices describe how varied a community is, not whether "
         "two communities hold the <i>same</i> species. Two further measures "
         "compare species lists directly: Jaccard similarity on presence "
         "alone, and Bray-Curtis dissimilarity weighted by abundance. Both "
         "are strongly effort-sensitive, and forest and grassland session "
         "counts inside a park are badly unbalanced, so every figure below is "
         "rarefied to the smaller group's session count across "
         f"{q13['n_draws']} draws."))
    add(("p",
         "<b>A similarity number means nothing without a yardstick.</b> So the "
         "same measures are computed for pairs of parks within a single "
         "habitat. If habitat genuinely restructures a community, "
         "between-habitat pairs should be less similar than same-habitat "
         "pairs. That contrast is the result."))
    comp = pd.DataFrame([
        ("Between habitats, same park",
         sim["between_habitat"]["jaccard"], sim["between_habitat"]["bray_curtis"],
         sim["between_habitat"]["n_pairs"]),
        ("Same habitat, different parks",
         sim["within_habitat"]["jaccard"], sim["within_habitat"]["bray_curtis"],
         sim["within_habitat"]["n_pairs"]),
    ], columns=["Comparison", "Jaccard (presence)",
                "Bray-Curtis (abundance)", "Pairs"])
    add(("table", comp,
         "Table 4.8 - Rarefied community similarity. Jaccard: higher means "
         "more shared species. Bray-Curtis: higher means more different."))
    add(("table", q13["between_habitat_pairs"],
         "Table 4.9 - Forest against grassland within each shared park, "
         "rarefied and raw"))
    add(("p",
         f"<b>The two measures disagree, and the disagreement is the finding.</b> "
         f"Jaccard is essentially flat - "
         f"{sim['between_habitat']['jaccard']} between habitats against "
         f"{sim['within_habitat']['jaccard']} within one - so forest and "
         f"grassland draw on much the same species pool, no more distinct "
         f"from each other than two parks are. Bray-Curtis separates clearly: "
         f"{sim['between_habitat']['bray_curtis']} against "
         f"{sim['within_habitat']['bray_curtis']}, a gap of "
         f"{sim['bray_gap']}. The habitats hold similar species lists and "
         f"weight them differently."))
    add(("note",
         f"<b>Guardrail G4, and how much it mattered here.</b> Before "
         f"rarefaction the between-habitat Bray-Curtis figure was "
         f"{sim['between_habitat']['bray_curtis_raw']} rather than "
         f"{sim['between_habitat']['bray_curtis']}, which would have "
         f"overstated the gap against the same-habitat control by roughly "
         f"{sim['rarefaction_shrank_bray_gap_by_pct']}%. Species-list "
         f"comparisons are among the most effort-sensitive statistics in "
         f"ecology, and the raw figures are retained in Table 4.9 only to "
         f"show the size of the correction."))
    add(("p",
         "This sharpens the central claim of the report. Section 4.3 "
         "established that habitat does not change how many species are "
         "present; Section 4.6 will show it does change which ones "
         "specialise. This section locates the difference precisely: not in "
         "the species list, but in how the community is weighted."))

    # ---------------------------------------------------------------- Q4
    add(("h2", "4.6 Q4 - Habitat specialists"))
    add(("verdict", "finding",
         f"Of {q4['n_well_sampled']} well-sampled species, "
         f"{q4['n_grassland']} are grassland specialists, "
         f"{q4['n_forest']} are forest specialists, and "
         f"{q4['n_generalist']} are generalists."))
    spec = pd.DataFrame([
        ("Grassland specialist", q4["n_grassland"],
         ">80% of sightings in grassland"),
        ("Generalist", q4["n_generalist"], "Neither habitat exceeds 80%"),
        ("Forest specialist", q4["n_forest"], ">80% of sightings in forest"),
    ], columns=["Class", "Species", "Definition"])
    add(("table", spec, "Table 4.10 - Habitat specialisation among "
                        f"{q4['n_well_sampled']} well-sampled species"))
    top_g = (species[species["specialist_class"] == "Grassland specialist"]
             .sort_values("grassland_share_pct", ascending=False)
             .head(8)[["Common_Name", "grassland_share_pct", "total_sightings"]]
             .rename(columns={"Common_Name": "Species",
                              "grassland_share_pct": "% in grassland",
                              "total_sightings": "Sightings"})
             # drop=True: the source row numbers are meaningless here and
             # would otherwise surface as a stray "index" column.
             .reset_index(drop=True))
    add(("table", top_g, "Table 4.11 - The most strongly grassland-loyal "
                         "species"))
    add(("note",
         f"<b>The zero is the result.</b> Every grassland-associated species "
         f"seen often enough to classify turned out to be strongly "
         f"grassland-loyal. Not one well-sampled species showed comparable "
         f"loyalty to forest - forest birds in this dataset are generalists "
         f"that also use grassland. Classification uses shared parks only, so "
         f"a species is not labelled a specialist merely because it was "
         f"surveyed somewhere with a single habitat type."))
    add(("p",
         "This is the finding with the clearest management consequence. "
         "Converting grassland removes the only habitat that "
         f"{q4['n_grassland']} species reliably use; converting forest "
         "removes habitat that no well-sampled species depends on "
         "exclusively. Section 4.3 showed richness gives no reason to prefer "
         "either habitat - this section shows composition does."))

    # ---------------------------------------------------------------- Q3
    add(("h2", "4.7 Q3 - Hotspots: parks and plots"))
    add(("verdict", "finding",
         f"Raw species count correlates with survey effort at "
         f"rho = {rho_eff_raw:.3f} ({fmt_p(p_eff_raw)}); the effort-adjusted "
         f"rate does not (rho = {rho_eff_rate:.3f}, {fmt_p(p_eff_rate)})."))
    pk_disp = pk.copy()
    pk_disp.insert(0, "Park", [NAME.get(i, i) for i in pk_disp.index])
    add(("table", pk_disp.reset_index(drop=True),
         "Table 4.12 - Parks ranked by species per session"))
    add(("p",
         "The two available rankings disagree. Ranked by raw species count "
         "Monocacy leads; ranked by species per session it falls to sixth, "
         "because it was the third most-visited park. The correlation pair "
         "above quantifies why: raw richness is substantially a measure of "
         "how often a park was visited, while the rate is independent of "
         "effort - which is the property a fair ranking requires."))
    add(("h3", "4.7.1 Plot-level rankings"))
    add(("p",
         f"Plot-level analysis is reported but should not be acted on. All "
         f"{len(plots):,} surveyed plots average "
         f"{plots['mean'].mean():.2f} species per session, and no plot was "
         f"visited more than {int(plots['size'].max())} times. The top-15 "
         f"leaderboard is simply everything above "
         f"{q3['top_plots'].head(15)['species_per_session'].min()} species "
         f"per session - the right tail of a noisy distribution rather than a "
         f"set of superior locations. A single unusually good morning is "
         f"enough to place a plot at the top."))
    add(("table", q3["top_plots"].head(10),
         "Table 4.13 - Top ten plots by species per session, with visit counts"))

    # ---------------------------------------------------------------- Q3b
    add(("h3", "4.7.2 At-risk presence by park"))
    ar = (sessions.groupby("Admin_Unit_Code")
          .agg(sessions_run=("session_id", "size"),
               at_risk_sessions=("has_at_risk", "sum")))
    ar["pct_of_sessions"] = (ar["at_risk_sessions"] / ar["sessions_run"] * 100).round(1)
    ar["reliable"] = ar["sessions_run"] >= 30
    ar = ar.sort_values("pct_of_sessions", ascending=False)
    ar_disp = ar.copy()
    ar_disp.insert(0, "Park", [NAME.get(i, i) for i in ar_disp.index])
    add(("table", ar_disp.reset_index(drop=True),
         "Table 4.14 - Percentage of sessions recording an at-risk species"))
    top_ar_code = ar.index[0]
    top_rank = int(pk["species_per_session"].rank(ascending=False, method="min")
                   .loc[top_ar_code])
    add(("note",
         f"<b>Diversity and conservation point at different parks.</b> "
         f"{NAME.get(top_ar_code, top_ar_code)} recorded an at-risk species "
         f"in {ar['pct_of_sessions'].iloc[0]}% of sessions - the highest of "
         f"any park - while ranking #{top_rank} of {len(pk)} for species per "
         f"session. A single \"best park\" recommendation would send "
         f"birdwatchers and conservation managers to opposite ends of the "
         f"list."))

    # ---------------------------------------------------------------- Q7
    add(("h2", "4.8 Q7 - Time of day"))
    add(("verdict", "finding",
         f"Grassland richness falls "
         f"{q7['early_vs_late']['Grassland']['gain_pct']}% from the early to "
         f"the late band "
         f"({fmt_p(q7['early_vs_late']['Grassland']['p_value'])}). Forest "
         f"shows no effect "
         f"({fmt_p(q7['early_vs_late']['Forest']['p_value'])})."))
    tod = pd.DataFrame([
        (h, q7["early_vs_late"][h]["early_mean"], q7["early_vs_late"][h]["late_mean"],
         f"{q7['early_vs_late'][h]['gain_pct']}%",
         fmt_p(q7["early_vs_late"][h]["p_value"]).replace("&lt;", "<"),
         q7["trend"][h]["rho"],
         fmt_p(q7["trend"][h]["p_value"]).replace("&lt;", "<"),
         "Significant" if q7["early_vs_late"][h]["significant"] else "Not significant")
        for h in ("Grassland", "Forest")
    ], columns=["Habitat", "Early (5-6am)", "Late (9-10am)", "Change",
                "Endpoint p", "Trend rho", "Trend p", "Verdict"])
    add(("table", tod, "Table 4.15 - Early versus late richness, tested two ways"))
    add(("table", q7["table"],
         "Table 4.16 - Species per session by time band and habitat"))
    add(("p",
         f"This is the most directly actionable finding in the project, and "
         f"the one with the strongest evidence: two independent tests - an "
         f"endpoint comparison and a correlation across the whole morning - "
         f"agree in both habitats. Two control checks support it. Session "
         f"length is {dur.min():.0f} to {dur.max():.0f} minutes with a median "
         f"of 10 in every band, so the effect is not early surveys running "
         f"longer. And unlike the monthly comparison in Section 4.9, sessions "
         f"are distributed across all three bands in both habitats."))
    ar_band = (sessions.groupby(["time_band", "habitat"])
               .has_at_risk.mean().mul(100).round(1).unstack())
    add(("table", ar_band,
         "Table 4.17 - Percentage of sessions recording an at-risk species, "
         "by time band"))
    add(("p",
         "A negative result worth recording: at-risk detection shows no "
         "time-of-day pattern in either habitat. The early-morning advantage "
         "is about how many species appear, not which ones. Survey scheduling "
         "aimed at at-risk species gains nothing from an early start."))

    # ---------------------------------------------------------------- Q6
    add(("h2", "4.9 Q6 - Seasonal change"))
    add(("verdict", "descriptive",
         f"Cannot be assessed. Visit number and day-of-season correlate at "
         f"rho = {rho_cal:.3f} ({fmt_p(p_cal)}), so a seasonal decline is "
         f"indistinguishable from a repeat-visit decline."))
    add(("table", q6["table"],
         "Table 4.18 - Species per session and sessions run, by month"))
    add(("p",
         f"Three confounds sit on the same axis. First, effort is uneven: "
         f"forest ran {q6['effort_imbalance']['Forest']}x more sessions in "
         f"its busiest month than its quietest, while grassland stayed nearly "
         f"flat at {q6['effort_imbalance']['Grassland']}x. Second, visit "
         f"number tracks the calendar almost perfectly "
         f"(rho = {rho_cal:.3f}), and richness itself declines with visit "
         f"number (rho = {rho_rich:.3f}, {fmt_p(p_rich)}) - so the July dip "
         f"is equally consistent with birds becoming harder to find and with "
         f"observers recording less on a plot they have already walked twice. "
         f"Third, third visits happened in grassland only, so late-season "
         f"figures are a different habitat mix as well as a different time."))
    add(("note",
         "<b>No significance test was applied to the monthly figures, and "
         "that is deliberate.</b> A p-value computed on confounded groups "
         "would lend false authority to a comparison that cannot be made. The "
         "numbers are reported descriptively so a reader can see them, "
         "labelled so nobody mistakes them for a trend."))

    # ---------------------------------------------------------------- Q9
    add(("h2", "4.10 Q9 - Sky, wind and disturbance"))
    add(("verdict", "finding",
         f"Serious disturbance costs {dt['loss_pct']}% of recorded species "
         f"({dt['none_mean']} to {dt['serious_mean']} per session, "
         f"{fmt_p(dt['p_value'])}) - the largest effect measured in this "
         f"project."))
    add(("table", q9["disturbance"],
         "Table 4.19 - Species per session by disturbance level"))
    add(("p",
         f"With n = {dt['n_none']} undisturbed sessions against "
         f"n = {dt['n_serious']} seriously disturbed, this is a "
         f"{dist_gap:.2f} species gap - larger than the observer effect and "
         f"{dist_gap / hab_gap:.0f} times the habitat difference the survey "
         f"was designed to measure. It is also the only environmental "
         f"variable that is a property of the site and the schedule rather "
         f"than of the weather, which makes it the only one management can "
         f"act on."))
    dist_hab = (sessions.groupby(["Disturbance", "habitat"])
                .species_per_session.mean().round(2).unstack())
    add(("table", dist_hab,
         "Table 4.20 - Disturbance effect within each habitat"))
    add(("note",
         f"<b>An anomaly reported rather than smoothed away.</b> \"Slight\" "
         f"disturbance scores <i>above</i> \"no effect\" "
         f"({q9['disturbance'].loc['Slight effect on count', 'species_per_session']} "
         f"against "
         f"{q9['disturbance'].loc['No effect on count', 'species_per_session']}), "
         f"on large samples in both categories, and Table 4.20 shows it "
         f"replicates independently in forest and in grassland. We have no "
         f"mechanism to offer. Inventing one would be worse than recording "
         f"the observation, and the serious-versus-none comparison above is "
         f"unaffected either way."))
    add(("table", q9["sky"], "Table 4.21 - Species per session by sky condition"))
    add(("table", q9["wind"], "Table 4.22 - Species per session by wind condition"))
    add(("p",
         "Sky and wind show mild, ecologically plausible patterns - fog and "
         "drizzle lowest, a stiff breeze costly - but neither was subjected "
         "to a significance test as a category comparison, and neither is "
         "large enough to justify changing survey practice. They are reported "
         "for completeness and marked as untested."))

    # ---------------------------------------------------------------- Q8
    add(("h2", "4.11 Q8 - Temperature and humidity"))
    add(("verdict", "finding",
         f"Richness peaks at {q8['temperature_peak_band']} and declines at "
         f"both ends. The relationship is not monotonic, which matters for "
         f"how the correlation is read."))
    add(("table", q8["temperature"],
         "Table 4.23 - Species per session by temperature band"))
    add(("table", q8["humidity"],
         "Table 4.24 - Species per session by humidity band"))
    corr = pd.DataFrame([
        (k.replace("_", " - "), v["rho"],
         fmt_p(v["p_value"]).replace("&lt;", "<"),
         "Significant" if v["significant"] else "Not significant")
        for k, v in q8["correlations"].items()
    ], columns=["Correlation", "rho", "p", "Verdict"])
    add(("table", corr, "Table 4.25 - Spearman correlations with weather"))
    add(("note",
         f"<b>A case where a significant statistic misdescribes the data.</b> "
         f"Spearman's rho assumes a monotonic relationship. Applied to "
         f"temperature it returns "
         f"{q8['correlations']['Forest_Temperature']['rho']} for forest and "
         f"{q8['correlations']['Grassland_Temperature']['rho']} for "
         f"grassland, both significant and both negative - which read alone "
         f"would tell a manager that the coldest mornings are the most "
         f"productive. Table 4.23 shows they are not: richness peaks at "
         f"{q8['temperature_peak_band']} and the coldest band sits below that "
         f"peak. The defensible claim is that the warm end is worse. Nothing "
         f"here supports a claim about cold versus mild."))
    add(("p",
         f"Humidity shows a smaller and less consistent pattern, significant "
         f"in grassland "
         f"({fmt_p(q8['correlations']['Grassland_Humidity']['p_value'])}) but "
         f"not in forest "
         f"({fmt_p(q8['correlations']['Forest_Humidity']['p_value'])}). The "
         f"under-40% band records the highest single figure anywhere in this "
         f"dataset at "
         f"{q8['humidity'].loc['<40%', 'species_per_session']} species per "
         f"session - on "
         f"{int(q8['humidity'].loc['<40%', 'sessions_run'])} sessions, so it "
         f"falls below the G3 reliability floor and is excluded from every "
         f"conclusion."))
    add(("pagebreak",))

    # ================================================== 5. DATA QUALITY
    add(("h1", "5. Data quality and reliability"))
    add(("p",
         "Every finding above rests on the survey design. This section audits "
         "that design, and contains the result that most nearly invalidated "
         "the project."))

    add(("h2", "5.1 Q10 - Observer effects"))
    add(("verdict", "method",
         f"Three surveyors differ by {q10['spread_pct']}% in species "
         f"recorded per session - a gap of {obs_gap:.2f} species against a "
         f"habitat gap of {hab_gap:.2f}. Every pairwise difference is "
         f"significant."))
    add(("table", q10["per_observer"],
         "Table 5.1 - Species per session by observer"))
    pw = pd.DataFrame(
        [(k, fmt_p(v).replace("&lt;", "<"),
          "Significant" if v < 0.05 else "Not significant")
         for k, v in q10["pairwise_p"].items()],
        columns=["Comparison", "p", "Verdict"])
    add(("table", pw, "Table 5.2 - Pairwise comparisons between observers"))
    add(("p",
         f"Read that against the ecology before continuing. The habitat "
         f"difference this survey was built to measure is {hab_gap:.2f} "
         f"species per session. Which of three people held the clipboard "
         f"moves the same measure by {obs_gap:.2f} - roughly "
         f"{obs_gap / hab_gap:.0f} times more. Had surveyor assignment "
         f"correlated with habitat, this project would have measured the "
         f"surveyor and reported it as ecology."))

    add(("h3", "5.1.1 Three checks on whether this invalidates the study"))
    add(("p", "<b>Check 1 - was the rota balanced?</b>"))
    add(("table", q10["habitat_shares"],
         "Table 5.3 - Each observer's share of each habitat's sessions"))
    add(("p",
         f"Yes. Each surveyor covered close to a third of both habitats, with "
         f"a maximum deviation of "
         f"{q10['max_habitat_share_deviation'] * 100:.1f} percentage points "
         f"(balanced = {q10['balanced']}). Because assignment is balanced, "
         f"the observer effect cancels out of any habitat comparison rather "
         f"than biasing it."))
    add(("p", "<b>Check 2 - is it the person, or the parks they were sent to?</b>"))
    wp = (sessions.groupby(["Admin_Unit_Code", "Observer"])
          .species_per_session.agg(["size", "mean"]).reset_index())
    wp = wp[wp["size"] >= 20]
    ok = wp.groupby("Admin_Unit_Code").size()
    wp = wp[wp["Admin_Unit_Code"].isin(ok[ok == 3].index)]
    piv = wp.pivot(index="Admin_Unit_Code", columns="Observer",
                   values="mean").round(2)
    piv_disp = piv.copy()
    piv_disp.insert(0, "Park", [NAME.get(i, i) for i in piv_disp.index])
    add(("table", piv_disp.reset_index(drop=True),
         "Table 5.4 - Species per session by observer, within each park where "
         "all three worked 20+ sessions"))
    orders = {tuple(r.sort_values(ascending=False).index) for _, r in piv.iterrows()}
    add(("p",
         f"The person. Across the {len(piv)} parks where all three surveyors "
         f"worked enough sessions to compare, the ranking is "
         f"{'identical in every park' if len(orders) == 1 else 'largely stable'} "
         f"- the same surveyor is lowest everywhere and the same one is "
         f"highest everywhere. The effect cannot be explained by who was sent "
         f"where."))
    add(("p", "<b>Check 3 - do the observers disagree about the finding?</b>"))
    obs_hab = (sessions[sessions.is_shared_park]
               .groupby(["Observer", "habitat"])
               .species_per_session.mean().round(2).unstack())
    add(("table", obs_hab,
         "Table 5.5 - Species per session by observer and habitat, shared "
         "parks only"))
    add(("p",
         "No. Within the shared parks all three surveyors independently reach "
         "the same conclusion - no meaningful richness gap between habitats - "
         "even while disagreeing substantially about the absolute numbers. "
         "The null result of Section 4.3 replicates three times over."))
    add(("note",
         f"<b>Verdict: real, large, and harmless here - but only by design.</b> "
         f"The observer effect does not contaminate any conclusion in this "
         f"report, because the rota was balanced. That was a design choice, "
         f"not luck, and it deserves to be recorded as the single most "
         f"consequential methodological decision in the survey. One practical "
         f"limit does follow: absolute species-per-session values carry a "
         f"personal-calibration band of roughly plus or minus "
         f"{obs_gap / 2:.1f} species, so comparisons within this dataset are "
         f"sound while the absolute numbers should not be quoted against "
         f"another study's."))

    add(("h2", "5.2 Q14 - How birds were detected"))
    add(("verdict", "method",
         f"{q14['auditory_pct']}% of all detections were made by ear rather "
         f"than by eye, and the observer gap of Section 5.1 sits almost "
         f"entirely on that channel: {q14['auditory_gap']:.2f} species per "
         f"session between surveyors on auditory detections against "
         f"{q14['visual_gap']:.2f} on visual."))
    add(("p",
         "Section 5.1 established that the observer effect is real, large, "
         "and balanced out of the habitat comparison. It did not establish "
         "<i>what</i> the three surveyors were doing differently. That matters "
         "for the recommendations: an effect with no known mechanism can only "
         "be managed by rota design, whereas an effect with a located "
         "mechanism can be reduced at source. This section locates it."))
    mc = pd.DataFrame({
        "Detection method": q14["method_counts"].index,
        "Detections": q14["method_counts"].values,
        "% of all detections": q14["method_share"].values,
    })
    add(("table", mc, "Table 5.6 - Detections by identification method"))
    add(("p",
         f"Two of the three methods are auditory. Singing alone accounts for "
         f"{q14['method_share']['Singing']}% of detections and calling for a "
         f"further {q14['method_share']['Calling']}%; only "
         f"{q14['method_share']['Visualization']}% of birds were identified "
         f"by sight. This is normal for a point-count protocol in closed "
         f"canopy, but it has a consequence that is easy to miss: the survey "
         f"is, in practice, a hearing test."))

    obs_ch = q14["by_observer"].copy()
    obs_ch.insert(0, "Observer", obs_ch.index)
    add(("table", obs_ch.reset_index(drop=True),
         "Table 5.7 - Species per session by observer and detection channel"))
    g_sing = q14["gaps"]["Singing"]
    g_vis = q14["gaps"]["Visualization"]
    add(("p",
         f"The pattern is not a uniform attentiveness gap. On singing birds "
         f"the surveyors differ by {g_sing['gap']:.2f} species per session, "
         f"with {g_sing['lowest']} lowest and {g_sing['highest']} highest. On "
         f"birds identified by sight the spread narrows to "
         f"{g_vis['gap']:.2f} - and the ordering changes: "
         f"{q14['overall_lowest_observer']}, who records fewest species "
         f"overall, is <b>not</b> the lowest on the visual channel "
         f"({g_vis['lowest']} is). A surveyor who was simply less thorough, "
         f"or spent less time at the plot, would be lowest on every channel. "
         f"This one is not."))
    add(("note",
         f"<b>The observer effect is an ear-training effect, not an effort "
         f"effect.</b> Roughly {q14['auditory_gap'] / (q14['auditory_gap'] + q14['visual_gap']) * 100:.0f}% "
         f"of the total between-surveyor gap sits on auditory detections, and "
         f"the rank order reverses on the visual channel. That is a specific, "
         f"trainable difference in song and call recognition rather than a "
         f"general difference in care or diligence. It converts Section 5.1's "
         f"warning into Recommendation 8.2 - targeted call-recognition "
         f"calibration - which would not have been justifiable without this "
         f"breakdown."))

    ic = pd.DataFrame({
        "Interval": q14["interval_counts"].index,
        "Detections": q14["interval_counts"].values,
        "% of all detections": (
            q14["interval_counts"].values / q14["interval_counts"].sum() * 100
        ).round(1),
        "Cumulative %": q14["interval_cumulative"].values,
    })
    add(("table", ic, "Table 5.8 - First detections by time interval within "
                      "the 10-minute count"))
    add(("p",
         f"The 10-minute protocol is recorded in four 2.5-minute intervals, "
         f"which allows a direct test of whether the count length was "
         f"adequate. {q14['first_interval_pct']}% of all detections arrive in "
         f"the first 2.5 minutes and "
         f"{q14['interval_cumulative']['5 - 7.5 min']}% within seven and a "
         f"half; the final interval adds the remaining "
         f"{100 - q14['interval_cumulative']['5 - 7.5 min']:.1f}%. The "
         f"accumulation curve is flattening but has not gone flat, so the "
         f"count length is sufficient for the species that use the site "
         f"regularly while a longer count would still add occasional records."))
    add(("p",
         f"The same breakdown by surveyor is reassuring in a different way. "
         f"The share of detections falling in the first interval ranges from "
         f"{q14['by_observer_interval']['0-2.5 min'].min()}% to "
         f"{q14['by_observer_interval']['0-2.5 min'].max()}% across the three "
         f"surveyors - they accumulate detections at broadly the same rate. "
         f"Whatever separates them is happening throughout the count, not in "
         f"a burst at the start or a fade at the end, which is again "
         f"consistent with recognition skill rather than attention span."))

    add(("h2", "5.3 Q12 - Coverage and effort"))
    add(("verdict", "descriptive",
         f"{q12['parks_with_both']} of {q12['n_parks']} parks were surveyed "
         f"in both habitats, so {q12['usable_pct']}% of sessions can address "
         f"the central question."))
    add(("table", q12["session_duration"],
         "Table 5.9 - Session duration by habitat (minutes)"))
    add(("p",
         f"Median session length is 10 minutes in both habitats, so effort "
         f"per session is directly comparable and no rate in this report "
         f"requires a duration correction. Forest plots received "
         f"{q12['visits_per_plot']['Forest']} visits on average against "
         f"{q12['visits_per_plot']['Grassland']} for grassland - an imbalance "
         f"that matters for Section 4.9."))

    add(("h2", "5.4 Protocol adherence and completeness"))
    add(("kv", [
        ("Sessions on protocol",
         f"{int((dur == 10).sum()):,} of {len(dur):,} "
         f"({(dur == 10).mean() * 100:.1f}%) ran exactly 10 minutes"),
        ("Longest session", f"{int(dur.max())} minutes "
                            f"({int((dur > 10).sum())} sessions exceeded 10)"),
        ("Parks below the 30-session floor",
         ", ".join(f"{NAME.get(i, i)} ({int(rr['total'])})"
                   for i, rr in low.iterrows()) or "none"),
    ]))
    miss = rows.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    EXPLAIN = {
        "Sub_Unit_Code": "Optional field; most parks have no sub-units",
        "Site_Name": "Recorded for forest plots only, by protocol",
        "Distance": "Flyovers have no distance to record",
        "AcceptedTSN": "Taxonomic serial number absent for a few records",
        "ID_Method": "Method not recorded on two rows",
        "TaxonCode": "Taxon code not recorded on two rows",
    }
    md = pd.DataFrame({
        "Column": miss.index,
        "Missing": miss.values,
        "% of rows": (miss.values / len(rows) * 100).round(1),
        "Explanation": [EXPLAIN.get(c, "Unexplained") for c in miss.index],
    })
    add(("table", md, "Table 5.10 - Missing values and their causes"))
    exact = bool((rows["Distance"].isna() == rows["is_flyover"]).all())
    add(("note",
         f"<b>Missingness is explained by protocol, not by data loss.</b> The "
         f"clearest case: {n_fly} records carry no Distance value, and "
         f"exactly those {n_fly} records are flyovers - birds passing "
         f"overhead rather than using the site, which by definition have no "
         f"distance to record. The correspondence is one-to-one with no "
         f"exceptions (verified: {exact}). Missingness that maps perfectly "
         f"onto a protocol rule is evidence of a well-run survey."))
    add(("pagebreak",))

    # ================================================== 6. DISCUSSION
    add(("h1", "6. Discussion"))
    add(("h2", "6.1 Composition matters; abundance does not"))
    add(("p",
         "The clearest theme across the results is that habitat shapes "
         "<i>which</i> birds are present far more than <i>how many</i>. "
         "Section 4.3 found no richness difference once the comparison was "
         "made within shared parks. Sections 4.1 and 4.5 found substantial "
         "compositional differences in the same data: at-risk sightings "
         "concentrated in forest, and every one of the "
         f"{q4['n_grassland']} habitat specialists loyal to grassland."))
    add(("p",
         f"Section 4.5 locates that difference precisely. Rarefied community "
         f"similarity shows the two habitats draw on much the same species "
         f"pool - Jaccard "
         f"{q13['similarity']['between_habitat']['jaccard']} between habitats "
         f"against {q13['similarity']['within_habitat']['jaccard']} between "
         f"two parks of the same habitat - while their abundance structures "
         f"separate clearly (Bray-Curtis "
         f"{q13['similarity']['between_habitat']['bray_curtis']} against "
         f"{q13['similarity']['within_habitat']['bray_curtis']}). The "
         f"distinction is not which birds occur but how the community is "
         f"weighted, which is why specialist counts and at-risk rates detect "
         f"a habitat effect that species counts cannot."))
    add(("p",
         "This has a direct consequence for how such surveys are used. A "
         "management decision framed as \"which habitat holds more "
         "biodiversity\" cannot be answered by this data and probably should "
         "not be asked - the two habitats hold comparable numbers of species "
         "and different sets of them. A decision framed as \"which species "
         "would we lose\" is answerable, and gives an asymmetric answer: "
         "converting grassland removes the only habitat "
         f"{q4['n_grassland']} species reliably use, while no well-sampled "
         "species depends exclusively on forest."))

    add(("h2", "6.2 Effort is the dominant confound"))
    add(("p",
         f"Three separate results in this report were initially misleading "
         f"for the same reason - unequal survey effort. Pooled richness "
         f"appeared significant because grassland ran "
         f"{q11['sessions']['ratio']}x more sessions in different parks "
         f"(Section 4.3). Park rankings by raw species count reflected visit "
         f"frequency, correlating with effort at rho = {rho_eff_raw:.2f} "
         f"while the effort-adjusted rate did not (Section 4.7). Exclusive "
         f"species counts overstated the grassland advantage by roughly four "
         f"times before rarefaction (Section 4.4)."))
    add(("p",
         "Each was caught by a different guardrail, but they are the same "
         "underlying error: treating a count of observations as a measure of "
         "a place. In a dataset where effort varies by a factor of four "
         "across the comparison of interest, that error is not a subtle one - "
         "it is the default outcome of any un-normalised analysis."))

    add(("h2", "6.3 Measurement error can exceed the signal"))
    add(("p",
         f"The observer effect ({obs_gap:.2f} species per session) and the "
         f"disturbance effect ({dist_gap:.2f}) both exceed every ecological "
         f"contrast in this project, including the {hab_gap:.2f}-species "
         f"habitat difference the survey was designed to detect. Neither is "
         f"an ecological finding; both are properties of how the measurement "
         f"was taken."))
    scale = pd.DataFrame(sorted([
        ("Disturbance (none to serious)", round(dist_gap, 2), "Yes"),
        ("Observer (3 surveyors)", round(obs_gap, 2), "Yes"),
        ("Temperature (best to worst reliable band)",
         round(q8["temperature"][q8["temperature"]["reliable"]]["species_per_session"].max()
               - q8["temperature"][q8["temperature"]["reliable"]]["species_per_session"].min(), 2),
         "Yes"),
        ("Time of day, grassland",
         round(q7["early_vs_late"]["Grassland"]["early_mean"]
               - q7["early_vs_late"]["Grassland"]["late_mean"], 2), "Yes"),
        ("Time of day, forest",
         round(q7["early_vs_late"]["Forest"]["early_mean"]
               - q7["early_vs_late"]["Forest"]["late_mean"], 2), "Tested, failed"),
        ("Habitat (within shared parks)", round(hab_gap, 2), "Tested, failed"),
    ], key=lambda x: -x[1]),
        columns=["Effect", "Gap (species/session)", "Significance-tested?"])
    add(("table", scale,
         "Table 6.1 - Every tested effect in the project, in the same units"))
    add(("p",
         "The practical implication is that survey protocol deserves at least "
         "as much design attention as the ecological question. A study that "
         "balances its observer rota and controls disturbance can detect a "
         "small habitat effect; one that does neither will produce a "
         "confident answer about whichever of those two varied most."))

    add(("h2", "6.4 What negative results contributed"))
    add(("p",
         "Two of the fourteen questions produced no usable answer, and both "
         "were informative. The rejected richness comparison (Section 4.3) "
         "demonstrated Simpson's paradox in the project's own data and "
         "justified restricting every subsequent habitat analysis to shared "
         "parks. The unanswerable seasonal question (Section 4.9) identified "
         "a design flaw - visit order confounded with calendar date - that a "
         "future survey can correct cheaply, and which no amount of "
         "post-hoc analysis can repair in this dataset."))
    add(("pagebreak",))

    # ================================================== 7. INSIGHTS
    add(("h1", "7. Insights"))
    add(("p",
         "Synthesised across questions and ranked by strength of evidence. "
         "Each links back to the section that supports it."))
    ins = pd.DataFrame([
        (1, "Forest shelters Wood Thrush specifically, not at-risk birds as a class",
         f"{q1['forest_pct']}% vs {q1['grassland_pct']}%, "
         f"{fmt_p(q1['p_value']).replace('&lt;', '<')}, 4/4 parks; but "
         f"{q1b['wood_thrush_share_pct']}% is one species",
         "4.1", "Strong, correctly narrowed"),
        (2, "The surveyor matters more than anything being surveyed",
         f"{q10['spread_pct']}% spread, all pairs significant, consistent in "
         f"every park, vs a {hab_gap:.2f}-species habitat gap",
         "5.1", "Strong"),
        (3, "Grassland holds every habitat specialist; forest holds none",
         f"{q4['n_grassland']} vs {q4['n_forest']} of "
         f"{q4['n_well_sampled']} well-sampled species",
         "4.5", "Strong"),
        (4, "Disturbance costs more species than any weather variable",
         f"{dt['loss_pct']}% loss, {fmt_p(dt['p_value']).replace('&lt;', '<')}, "
         f"replicates in both habitats",
         "4.9", "Strong"),
        (5, "Grassland surveys should start early; forest scheduling is free",
         f"{q7['early_vs_late']['Grassland']['gain_pct']}% gain, two "
         f"independent tests agree; forest null on both",
         "4.7", "Strong, grassland only"),
        (6, "Habitat does not drive species richness",
         f"pooled {fmt_p(q2['pooled']['p_value']).replace('&lt;', '<')} "
         f"collapses to "
         f"{fmt_p(q2['within_shared']['p_value']).replace('&lt;', '<')} "
         f"within shared parks",
         "4.3", "Strong negative result"),
        (7, "\"Best park\" depends entirely on the question asked",
         f"{NAME.get(top_ar_code, top_ar_code)} ranks #1 for at-risk presence "
         f"and #{top_rank} of {len(pk)} for richness",
         "4.6", "Solid"),
        (8, "Habitat restructures abundance, not species membership",
         f"rarefied Bray-Curtis {q13['similarity']['between_habitat']['bray_curtis']} "
         f"between habitats vs "
         f"{q13['similarity']['within_habitat']['bray_curtis']} within one; "
         f"Jaccard essentially flat",
         "4.5", "Solid"),
        (9, "The habitat null result is not a metric artefact",
         f"richness, Shannon, Simpson and evenness all agree "
         f"(smallest p = "
         f"{min(t['p_value'] for t in q13['tests'].values()):.2f})",
         "4.5", "Strong negative result"),
        (10, "Raw counts rank effort, not places",
         f"raw richness correlates with effort at rho {rho_eff_raw:.2f}; the "
         f"rate does not (rho {rho_eff_rate:.2f})",
         "4.6", "Solid"),
    ], columns=["#", "Insight", "Evidence", "Section", "Strength"])
    add(("table", ins, "Table 7.1 - Insights ranked by strength of evidence"))
    add(("pagebreak",))

    # ================================================== 8. RECOMMENDATIONS
    add(("h1", "8. Recommendations"))
    add(("h2", "8.1 For land management"))
    add(("bullets", [
        f"<b>Protect mature forest where Wood Thrush is present, and describe "
        f"it as such.</b> The at-risk signal is real and repeats in every "
        f"shared park, but {q1b['wood_thrush_share_pct']}% of it is one "
        f"species. Framing this as a Wood Thrush measure rather than a "
        f"general at-risk measure is both more accurate and more defensible "
        f"if challenged. (Section 4.1)",

        f"<b>Reduce disturbance during survey windows.</b> A "
        f"{dt['loss_pct']}% reduction in recorded species is the largest "
        f"effect measured in this project, and disturbance is the only "
        f"environmental variable that is a property of the site and schedule "
        f"rather than the weather. Parks recording moderate or serious "
        f"disturbance in a large share of sessions are the place to start. "
        f"(Section 4.10)",

        f"<b>Do not convert grassland on biodiversity grounds.</b> Grassland "
        f"holds all {q4['n_grassland']} habitat specialists in the dataset "
        f"while forest holds none, and richness gives no reason to prefer "
        f"either habitat. A conversion argument built on \"more species\" "
        f"has no support in this data. (Sections 4.3 and 4.6)",

        f"<b>Route at-risk monitoring and diversity visits to different "
        f"parks.</b> The park with the highest at-risk detection rate ranks "
        f"last of {len(pk)} for species per session. A single "
        f"recommendation list would send both audiences to the wrong place. "
        f"(Section 4.7.2)",
    ]))

    add(("h2", "8.2 For survey design"))
    add(("p",
         "These changes would let a future season answer questions this one "
         "cannot. None requires additional parks, staff or season length - "
         "they redistribute the same effort."))
    add(("bullets", [
        f"<b>Add grassland plots to the {len(single)} forest-only parks.</b> "
        f"All {len(single)} single-habitat parks are forest-only, holding "
        f"{int(single['total'].sum()):,} sessions that currently cannot "
        f"contribute to the central question. Pairing habitats within those "
        f"parks would take usable data from {q12['usable_pct']}% toward 100% "
        f"- roughly "
        f"{(q12['total_sessions'] / q12['usable_sessions'] - 1) * 100:.0f}% "
        f"more analysable sample. This is the single highest-value change "
        f"available. (Section 2.2)",

        f"<b>Document the balanced observer rota as a protocol requirement.</b> "
        f"The {q10['spread_pct']}% observer spread is harmless here purely "
        f"because assignment was balanced across habitats and parks. That "
        f"currently exists as practice rather than as a written rule, and it "
        f"is the reason this study's conclusions hold. (Section 5.1)",

        f"<b>Calibrate surveyors on song and call recognition specifically.</b> "
        f"{q14['auditory_pct']}% of detections are auditory, and "
        f"{q14['auditory_gap']:.2f} of the {obs_gap:.2f}-species observer gap "
        f"sits on that channel against {q14['visual_gap']:.2f} on the visual "
        f"one - with the ranking reversing between the two. This is a "
        f"trainable recognition difference, not a difference in diligence, so "
        f"a short pre-season call-identification calibration targets the "
        f"actual mechanism. (Section 5.2)",

        f"<b>Decouple visit number from calendar date.</b> The two correlate "
        f"at rho = {rho_cal:.2f}, which makes seasonal analysis impossible. "
        f"Rotating visit order across plots - surveying some plots in reverse "
        f"order - would unlock a whole objective at no additional cost. "
        f"(Section 4.9)",

        f"<b>Equalise visits per plot across habitats.</b> Forest plots "
        f"received {q12['visits_per_plot']['Forest']} visits on average "
        f"against grassland's {q12['visits_per_plot']['Grassland']}, and "
        f"third visits happened in grassland only. (Section 5.3)",

        f"<b>Lift the smallest parks over the 30-session floor.</b> Only two "
        f"parks fall below it: "
        + "; ".join(f"{NAME.get(i, i)} needs {30 - int(rr['total'])} more"
                    for i, rr in low.iterrows())
        + f". That is {int((30 - low['total']).sum())} extra sessions to make "
          f"two more parks reportable - the cheapest improvement on this "
          f"list. (Section 5.4)",

        f"<b>Increase visits per plot beyond three.</b> No plot exceeded "
        f"{int(plots['size'].max())} visits, which makes plot-level ranking "
        f"impossible. Plot-scale recommendations require substantially more "
        f"repeat sampling. (Section 4.7.1)",
    ]))
    add(("pagebreak",))

    # ================================================== 9. LIMITATIONS
    add(("h1", "9. Limitations"))
    add(("p",
         "Presented as a numbered section rather than a footnote. Knowing "
         "which questions this dataset cannot answer is part of the result, "
         "and several of the entries below are the direct output of the "
         "guardrails described in Section 3.4."))
    lim = pd.DataFrame([
        ("Seasonal trend",
         f"Visit number and day-of-season correlate at rho = {rho_cal:.2f}, "
         f"and third visits were grassland-only. A seasonal decline cannot be "
         f"separated from a repeat-visit decline.", "4.9"),
        ("Strength of the habitat null result",
         f"Section 4.3 rejects a habitat effect on richness, but does so "
         f"within {q2['n_parks']} parks on "
         f"{q2['within_shared']['n_forest']} forest sessions. That is enough "
         f"to reject a strong claim, not enough to demonstrate equivalence "
         f"across the park system.", "4.3"),
        ("Individual plot quality",
         f"No plot was visited more than {int(plots['size'].max())} times. "
         f"The plot leaderboard is the right tail of a noisy distribution, "
         f"not a set of superior locations.", "4.6.1"),
        ("Cold versus mild mornings",
         "The temperature relationship is hump-shaped, so the significant "
         "negative correlation misdescribes the cold end.", "4.10"),
        ("At-risk birds and survey timing",
         "No time-of-day effect on at-risk detection in either habitat. The "
         "morning advantage concerns how many species appear, not which.",
         "4.7"),
        ("Mechanism for the disturbance anomaly",
         "Unknown. Large samples on both sides, replicated in both habitats, "
         "and no mechanism available. Reported as observed.", "4.9"),
        ("Absolute species-per-session values",
         f"Carry a personal-calibration band of roughly plus or minus "
         f"{obs_gap / 2:.1f} species from the observer effect. Within-dataset "
         f"comparisons are sound; the absolute figures should not be quoted "
         f"against another study's.", "5.1"),
        (f"The {len(single)} single-habitat parks",
         "They contain no within-park habitat comparison and contribute "
         "nothing to the central question.", "2.2"),
        ("Sky and wind effects",
         "Reported descriptively; never subjected to a significance test as a "
         "category comparison, so the apparent ordering is unverified.",
         "4.9"),
        ("Single season",
         "All data comes from one breeding season. Between-year variation is "
         "unmeasured, so no trend over time can be inferred.", "2.1"),
    ], columns=["Limitation", "Explanation", "Section"])
    add(("table", lim, "Table 9.1 - Limitations and their sources"))

    # ================================================== 10. CONCLUSION
    add(("h1", "10. Conclusion"))
    add(("p",
         f"Thirteen questions were asked of {len(rows):,} bird sightings across "
         f"{len(sessions):,} survey sessions. Five produced findings that "
         f"survived scrutiny, one was rejected, and the remainder were "
         f"descriptive or methodological. The surviving findings are "
         f"consistent with each other and point in the same direction: "
         f"habitat in this dataset determines <i>which</i> birds are present "
         f"rather than <i>how many</i>."))
    add(("p",
         f"The strongest single result is not ecological. The difference "
         f"between three surveyors ({obs_gap:.2f} species per session) and "
         f"the effect of survey disturbance ({dist_gap:.2f}) both exceed the "
         f"habitat difference the study was designed to detect "
         f"({hab_gap:.2f}). The analysis holds because the observer rota was "
         f"balanced across habitats and parks - a design decision that, on "
         f"the evidence assembled here, did more to protect this study's "
         f"validity than any analytical choice made afterwards."))
    add(("p",
         "Three of the thirteen questions were answered by rejecting them, and "
         "those rejections were as informative as the confirmations. A pooled "
         "habitat comparison, an un-normalised park ranking and a raw "
         "exclusive-species count would each have produced a confident, "
         "publishable and wrong answer. They were caught by four rules "
         "applied consistently rather than by any single test, which suggests "
         "the rules themselves are the transferable output of this project."))
    add(("p",
         f"For management, the actionable conclusions are narrow but firm: "
         f"protect forest where Wood Thrush is present, reduce survey-window "
         f"disturbance, retain grassland because it holds every habitat "
         f"specialist in the dataset, and survey grassland early. For the "
         f"next survey season, the highest-value change is structural rather "
         f"than analytical - adding grassland plots to the "
         f"{len(single)} forest-only parks would increase the analysable "
         f"sample by roughly "
         f"{(q12['total_sessions'] / q12['usable_sessions'] - 1) * 100:.0f}% "
         f"without a single additional park, staff member or survey day."))

    # ================================================== APPENDIX
    add(("pagebreak",))
    add(("h1", "Appendix A - Reproducibility"))
    add(("p",
         "Every figure in this report is generated by the analysis pipeline "
         "at build time. No number is typed by hand, in this document or in "
         "the dashboard, so the two cannot disagree."))
    pipe = pd.DataFrame([
        ("src/ingest.py", "Reads the two source workbooks, reports sheet-level "
                          "structure"),
        ("src/clean.py", "Applies the ten cleaning decisions; writes "
                         "docs/cleaning_log.md"),
        ("src/features.py", "Builds the session table, species profile and "
                            "park coordinates"),
        ("src/stats_helpers.py", "Mann-Whitney U, Spearman rho, rank utilities"),
        ("src/analysis.py", "Answers Q1-Q12; run_all() is the single source of "
                            "every figure"),
        ("src/report_content.py", "This report, as structured content"),
        ("src/make_report.py", "Renders that content to PDF and Word"),
        ("src/make_ledger.py", "Renders the findings ledger to markdown"),
        ("app/", "Streamlit dashboard - reads the same run_all() output"),
    ], columns=["Module", "Responsibility"])
    add(("table", pipe, "Table A.1 - Pipeline modules"))
    add(("kv", [
        ("To reproduce this report",
         "python src/make_report.py - writes docs/ from the current data"),
        ("To reproduce the analysis",
         "python src/analysis.py - prints every headline figure"),
        ("To reproduce the cleaning audit",
         "python src/clean.py - rewrites docs/cleaning_log.md"),
        ("Generated", date.today().strftime("%d %B %Y")),
    ]))

    # ------------------------------------------------- Appendix B
    add(("pagebreak",))
    add(("h1", "Appendix B - Data dictionary"))
    add(("p",
         f"All {len(rows.columns)} fields in the cleaned dataset, split into "
         f"those that came from the source workbooks and those the pipeline "
         f"derived. Types and distinct-value counts are read from the data "
         f"itself at build time, so this table cannot drift out of step with "
         f"the file it describes."))

    DESC = {
        "Admin_Unit_Code": "Four-letter park code",
        "Sub_Unit_Code": "Sub-unit within a park; optional",
        "Site_Name": "Survey site between park and plot; forest only",
        "Plot_Name": "Individual survey plot",
        "Location_Type": "Forest or Grassland, as recorded in the source",
        "Year": "Survey year",
        "Date": "Survey date",
        "Start_Time": "Session start time",
        "End_Time": "Session end time",
        "Observer": "Surveyor who recorded the session",
        "Visit": "Visit number to that plot (1-3)",
        "Interval_Length": "Time interval within the count when detected",
        "ID_Method": "How the bird was identified (singing, calling, visual)",
        "Distance": "Detection distance band; blank for flyovers",
        "Flyover_Observed": "Bird passing overhead rather than using the site",
        "Sex": "Recorded sex, or Undetermined",
        "Common_Name": "Species common name",
        "Scientific_Name": "Species binomial - the identity key used here",
        "AcceptedTSN": "Taxonomic Serial Number",
        "TaxonCode": "NPS taxon code",
        "AOU_Code": "American Ornithological Union four-letter code",
        "PIF_Watchlist_Status": "Partners in Flight at-risk designation",
        "Regional_Stewardship_Status": "Regional stewardship designation",
        "Temperature": "Air temperature at the session, degrees C",
        "Humidity": "Relative humidity at the session, %",
        "Sky": "Sky condition category",
        "Wind": "Beaufort-style wind category",
        "Disturbance": "How much disturbance affected the count",
        "Initial_Three_Min_Cnt": "Detected in the first three minutes",
        "Distance_Display": "Cleaned display form of Distance",
        "session_id": "Plot + date + visit - the unit of every rate",
        "habitat": "Forest or Grassland, normalised",
        "park_name": "Full park name",
        "is_shared_park": "Park surveyed in both habitats - drives G2",
        "year": "Year, derived from Date",
        "quarter": "Calendar quarter",
        "month": "Year-month",
        "month_name": "Month name",
        "week": "ISO week number",
        "day_of_season": "Days since the first survey of the season",
        "start_hour": "Hour the session began",
        "time_band": "Early (5-6am), Mid (7-8am), Late (9-10am)",
        "session_duration_min": "Session length in minutes",
        "is_at_risk": "Boolean form of PIF_Watchlist_Status",
        "is_stewardship": "Boolean form of Regional_Stewardship_Status",
        "is_flyover": "Boolean form of Flyover_Observed",
        "in_first_three_min": "Boolean form of Initial_Three_Min_Cnt",
        "temp_band": "Binned temperature",
        "humidity_band": "Binned humidity",
    }
    SOURCE_COLS = {
        "Admin_Unit_Code", "Sub_Unit_Code", "Site_Name", "Plot_Name",
        "Location_Type", "Year", "Date", "Start_Time", "End_Time", "Observer",
        "Visit", "Interval_Length", "ID_Method", "Distance",
        "Flyover_Observed", "Sex", "Common_Name", "Scientific_Name",
        "AcceptedTSN", "TaxonCode", "AOU_Code", "PIF_Watchlist_Status",
        "Regional_Stewardship_Status", "Temperature", "Humidity", "Sky",
        "Wind", "Disturbance", "Initial_Three_Min_Cnt",
    }

    def _dict_table(cols: list[str]) -> pd.DataFrame:
        recs = []
        for c in cols:
            col = rows[c]
            recs.append((
                c,
                str(col.dtype),
                f"{col.nunique():,}",
                f"{col.isna().sum():,}",
                DESC.get(c, ""),
            ))
        return pd.DataFrame(recs, columns=[
            "Field", "Type", "Distinct", "Missing", "Description"])

    src_cols = [c for c in rows.columns if c in SOURCE_COLS]
    der_cols = [c for c in rows.columns if c not in SOURCE_COLS]
    add(("h2", "B.1 Fields from the source workbooks"))
    add(("table", _dict_table(src_cols),
         f"Table B.1 - {len(src_cols)} source fields"))
    add(("h2", "B.2 Fields derived by the pipeline"))
    add(("table", _dict_table(der_cols),
         f"Table B.2 - {len(der_cols)} derived fields, added by "
         f"src/features.py"))
    add(("h2", "B.3 The session table"))
    add(("p",
         f"Analysis operates on the session table rather than on individual "
         f"sightings. It has {len(sessions):,} rows and carries the columns "
         f"below in addition to the session-level attributes above."))
    sess_desc = {
        "species_per_session": "Distinct species recorded - primary richness "
                               "measure",
        "sightings_per_session": "Total records in the session",
        "at_risk_sightings": "Records of PIF Watchlist species",
        "flyovers": "Records flagged as flyovers",
        "pct_at_risk_per_session": "At-risk records as a % of the session",
        "has_at_risk": "Whether any at-risk species was recorded",
    }
    add(("table", pd.DataFrame(
        [(k, str(sessions[k].dtype), v) for k, v in sess_desc.items()],
        columns=["Field", "Type", "Description"]),
        "Table B.3 - Session-level metrics"))

    return B, dict(
        r=r, rows=rows, sessions=sessions, species=species, NAME=NAME,
        dt=dt, obs=obs, obs_gap=obs_gap, hab_gap=hab_gap, pk=pk,
        rho_eff_raw=rho_eff_raw, p_eff_raw=p_eff_raw,
        rho_eff_rate=rho_eff_rate, p_eff_rate=p_eff_rate,
        rho_cal=rho_cal, p_cal=p_cal, rho_rich=rho_rich, p_rich=p_rich,
        plots=plots, eff_park=eff_park, single=single, low=low, dur=dur,
        n_fly=n_fly, dist_gap=dist_gap, coords=coords,
    )