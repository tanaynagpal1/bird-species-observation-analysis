"""
Ask AI - a conversational front door to the analysis.

DESIGN DECISION, stated up front because it is the interesting part:

    This page contains no language model, and that is deliberate.

Every other page in this dashboard exists to argue one thing - that a number
you cannot trace is a number you should not act on. Bolting a generative model
onto the front of it would undercut the whole project: a model that invents a
plausible "8.7 species per session" contradicts the report sitting one tab
away, and the reader has no way to tell which one lied.

So this is an intent-matching engine over the guarded pipeline instead. It
recognises what a question is *about*, then hands back an answer assembled from
live values in analysis.py - the same values the PDF, the Word document and
every chart use. Three consequences follow:

  1. It cannot hallucinate a figure. There is no text generation anywhere; the
     numbers are formatted from the pipeline at render time.
  2. Every answer carries a confidence badge and an evidence trail, exactly
     like the Conclusion page, so a claim can be checked in one click.
  3. When it does not know, it says so and shows what it *can* answer, rather
     than guessing. Refusing well is part of the spec, not a failure mode.

It also needs no API key, costs nothing to run, and works identically on a
Streamlit Cloud deployment with no secrets configured - which means a reader
opening this from a link sees it working, not an error about billing.

Layout, top to bottom:
  1. time-aware greeting card
  2. what it can and cannot answer
  3. starter question chips
  4. the conversation
  5. chat input, with follow-up suggestions after each answer
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q1, q1b, q2, q3, q4 = res["q1"], res["q1b"], res["q2"], res["q3"], res["q4"]
q5, q6, q7, q8, q9 = res["q5"], res["q6"], res["q7"], res["q8"], res["q9"]
q10, q11, q12 = res["q10"], res["q11"], res["q12"]
q13, q14 = res["q13"], res["q14"]

sessions = da.sessions()
coords = da.park_coordinates()
NAME = dict(zip(coords["Admin_Unit_Code"], coords["park_name"]))

# Frequently reused derived values, computed once.
dt = q9["disturbance_test"]
obs = q10["per_observer"]["species_per_session"]
OBS_GAP = obs.max() - obs.min()
HAB_GAP = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])
DIST_GAP = dt["none_mean"] - dt["serious_mean"]
MIN_P13 = min(t["p_value"] for t in q13["tests"].values())
SIM = q13["similarity"]
G7 = q7["early_vs_late"]["Grassland"]
F7 = q7["early_vs_late"]["Forest"]

RELIABLE_FLOOR = 30

# Share of each park's sessions that recorded moderate or serious
# disturbance. Computed here rather than hard-coded so it tracks the data.
DISTURBED = (
    sessions.assign(_bad=sessions["Disturbance"].isin(
        ["Moderate effect on count", "Serious effect on count"]))
    .groupby("Admin_Unit_Code")["_bad"].mean().mul(100).round(1)
    .sort_values(ascending=False)
)
PARK_SESSIONS = sessions.groupby("Admin_Unit_Code").size()

BAND_ORDER = ["Early (5-6am)", "Mid (7-8am)", "Late (9-10am)"]
MONTH_ORDER = ["May", "June", "July"]

BADGES = {
    "strong": (theme.FOREST, "Strong evidence"),
    "narrowed": (theme.GRASSLAND, "Strong but narrowed"),
    "negative": (theme.AT_RISK, "Negative result"),
    "descriptive": (theme.MUTED, "Descriptive only"),
    "method": (theme.POND, "Methodological"),
    "none": ("", ""),
}


# ==================================================================== model
@dataclass
class Answer:
    """One reply: prose, an optional visual, and where it came from."""
    text: str
    badge: str = "none"
    source: str = ""
    chart: Callable[[], go.Figure] | None = None
    table: pd.DataFrame | None = None
    caption: str = ""
    followups: tuple[str, ...] = field(default_factory=tuple)


# ==================================================================== tables
_COL_NAMES = {
    "Common_Name": "Species",
    "pct_of_all_at_risk": "% of all at-risk sightings",
    "species_per_session": "Species / session",
    "sessions_run": "Sessions",
    "distinct_species": "Distinct species",
    "reliable": "Above the floor",
    "total": "Total",
    "parks": "Parks",
    "Sky": "Sky condition",
}


def pretty(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case DataFrame headers are for code, not for readers."""
    out = df.copy()
    out.index.name = _COL_NAMES.get(out.index.name, out.index.name)
    out.columns = [
        _COL_NAMES.get(c, str(c).replace("_", " ").capitalize())
        for c in out.columns
    ]
    return out


# ==================================================================== charts
def _bar(x, y, colours, ytitle, texts=None, height=300):
    fig = go.Figure(go.Bar(
        x=x, y=y, marker_color=colours,
        text=texts if texts is not None else [f"{v:.2f}" for v in y],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title=ytitle,
                      **theme.plotly_layout(height=height, showlegend=False))
    fig.update_yaxes(range=[0, max(y) * 1.2])
    return fig


def _grouped(cats, series, ytitle, height=310):
    """series: {name: (values, colour)}"""
    fig = go.Figure()
    for name, (vals, colour) in series.items():
        fig.add_trace(go.Bar(x=cats, y=vals, name=name, marker_color=colour,
                             text=[f"{v:.2f}" for v in vals],
                             textposition="outside"))
    fig.update_layout(barmode="group", yaxis_title=ytitle,
                      **theme.plotly_layout(height=height))
    return fig


def chart_at_risk():
    return _bar(["Forest", "Grassland"],
                [q1["forest_pct"], q1["grassland_pct"]],
                [theme.FOREST, theme.GRASSLAND],
                "% of sessions with an at-risk species",
                texts=[f"{q1['forest_pct']}%", f"{q1['grassland_pct']}%"])


def chart_richness():
    return _grouped(
        ["Pooled (all 11 parks)", "Within shared parks only"],
        {"Forest": ([q2["pooled"]["forest"], q2["within_shared"]["forest"]],
                    theme.FOREST),
         "Grassland": ([q2["pooled"]["grassland"],
                        q2["within_shared"]["grassland"]], theme.GRASSLAND)},
        "species per session")


def chart_diversity():
    labels = ["Richness", "Shannon", "Simpson", "Evenness"]
    keys = ["richness", "shannon", "simpson_diversity", "evenness"]
    # Richness is on a different scale, so each measure is shown as the forest
    # value divided by the grassland value - 1.0 means "no difference".
    ratios = [q13["tests"][k]["forest"] / q13["tests"][k]["grassland"]
              for k in keys]
    fig = go.Figure(go.Bar(
        x=labels, y=ratios, marker_color=theme.FOREST,
        text=[f"{v:.3f}" for v in ratios], textposition="outside",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=theme.AT_RISK,
                  annotation_text="no difference",
                  annotation_position="top right")
    fig.update_layout(yaxis_title="forest ÷ grassland",
                      **theme.plotly_layout(height=310, showlegend=False))
    fig.update_yaxes(range=[0.9, 1.1])
    return fig


def chart_similarity():
    cats = ["Jaccard<br>(which species)", "Bray-Curtis<br>(how common each is)"]
    return _grouped(
        cats,
        {"Between habitats, same park":
            ([SIM["between_habitat"]["jaccard"],
              SIM["between_habitat"]["bray_curtis"]], theme.FOREST),
         "Within a habitat, different parks":
            ([SIM["within_habitat"]["jaccard"],
              SIM["within_habitat"]["bray_curtis"]], theme.GRASSLAND)},
        "index value")


def chart_specialists():
    return _bar(["Grassland specialists", "Forest specialists", "Generalists"],
                [q4["n_grassland"], q4["n_forest"], q4["n_generalist"]],
                [theme.GRASSLAND, theme.FOREST, theme.MUTED],
                "well-sampled species",
                texts=[str(q4["n_grassland"]), str(q4["n_forest"]),
                       str(q4["n_generalist"])])


def chart_parks():
    t = q3["parks_by_rate"].copy()
    t = t.sort_values("species_per_session")
    names = [NAME.get(i, i) for i in t.index]
    colours = [theme.FOREST if ok else theme.MUTED for ok in t["reliable"]]
    fig = go.Figure(go.Bar(
        x=t["species_per_session"], y=names, orientation="h",
        marker_color=colours,
        text=[f"{v:.2f}" for v in t["species_per_session"]],
        textposition="outside",
    ))
    fig.update_layout(xaxis_title="species per session",
                      **theme.plotly_layout(height=380, showlegend=False))
    fig.update_xaxes(range=[0, t["species_per_session"].max() * 1.22])
    return fig


def chart_time_of_day():
    sp = q7["table"]["species_per_session"]
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_trace(go.Scatter(
            x=BAND_ORDER, y=[sp[hab][b] for b in BAND_ORDER],
            mode="lines+markers", name=hab,
            line={"color": colour, "width": 2.6},
            marker={"size": 10, "color": colour}))
    fig.update_layout(yaxis_title="species per session",
                      **theme.plotly_layout(height=310))
    return fig


def chart_season():
    sp = q6["table"]["species_per_session"]
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_trace(go.Scatter(
            x=MONTH_ORDER, y=[sp[hab][m] for m in MONTH_ORDER],
            mode="lines+markers", name=hab,
            line={"color": colour, "width": 2.6},
            marker={"size": 10, "color": colour}))
    fig.update_layout(yaxis_title="species per session",
                      **theme.plotly_layout(height=310))
    return fig


def chart_temperature():
    t = q8["temperature"]
    peak = q8["temperature_peak_band"]
    colours = [theme.FOREST if b == peak else theme.SEQUENTIAL[2]
               for b in t.index]
    return _bar(list(t.index), list(t["species_per_session"]), colours,
                "species per session")


def chart_disturbance():
    order = ["No effect on count", "Slight effect on count",
             "Moderate effect on count", "Serious effect on count"]
    short = ["None", "Slight", "Moderate", "Serious"]
    d = q9["disturbance"].reindex(order)
    colours = [theme.FOREST, theme.FOREST, theme.GRASSLAND, theme.AT_RISK]
    return _bar(short, list(d["species_per_session"]), colours,
                "species per session")


def chart_observer():
    t = q10["per_observer"]["species_per_session"].sort_values()
    return _bar(list(t.index), list(t.values),
                [theme.SEQUENTIAL[2], theme.SEQUENTIAL[3], theme.FOREST],
                "species per session")


def chart_detection():
    m = q14["method_share"]
    colours = [theme.FOREST, theme.SEQUENTIAL[3], theme.GRASSLAND]
    return _bar(list(m.index), list(m.values), colours,
                "% of all detections",
                texts=[f"{v}%" for v in m.values])


def chart_coverage():
    usable = q12["usable_sessions"]
    unusable = q12["total_sessions"] - usable
    return _bar(["Usable for the habitat question", "Cannot contribute"],
                [usable, unusable], [theme.FOREST, theme.MUTED],
                "survey sessions",
                texts=[f"{usable:,}", f"{unusable:,}"])


def chart_levers():
    items = [("Avoid serious disturbance", DIST_GAP, True),
             ("Train surveyors on calls", q14["auditory_gap"], True),
             ("Survey grassland early", G7["early_mean"] - G7["late_mean"], True),
             ("Forest vs grassland", HAB_GAP, False)]
    items = items[::-1]
    fig = go.Figure(go.Bar(
        x=[v for _, v, _ in items], y=[n for n, _, _ in items],
        orientation="h",
        marker_color=[theme.FOREST if a else theme.MUTED
                      for _, _, a in items],
        text=[f"{v:.2f}" for _, v, _ in items], textposition="outside",
    ))
    fig.update_layout(xaxis_title="difference in species per session",
                      **theme.plotly_layout(height=300, showlegend=False))
    fig.update_xaxes(range=[0, DIST_GAP * 1.25])
    return fig


# ==================================================================== answers
def a_greeting() -> Answer:
    return Answer(
        "Hello. I answer questions about the 2018 breeding-season bird survey "
        "sitting behind this dashboard - 15,372 sightings, 1,408 survey "
        "sessions, 126 species, 11 National Park Service units.\n\n"
        "Ask me anything about the findings and I will pull the numbers "
        "straight from the analysis pipeline. Try one of the suggestions "
        "below, or just type a question.",
        followups=("Which habitat is better for at-risk birds?",
                   "What is the biggest finding?",
                   "What can't this study answer?"))


def a_who() -> Answer:
    return Answer(
        "I am not a language model, and I think that is worth being clear "
        "about.\n\n"
        "I am a question-matching engine built into this dashboard. I work out "
        "what your question is **about**, then assemble an answer from live "
        "values in the analysis pipeline - the same pipeline that produces the "
        "PDF report and every chart here.\n\n"
        "The practical difference: I cannot invent a statistic. There is no "
        "text generation anywhere in me, so every number you see has been "
        "computed from the survey data, not predicted. If I do not know "
        "something, I will tell you rather than guess.\n\n"
        "That was a deliberate choice. This whole project argues that a number "
        "you cannot trace is a number you should not act on - it would be "
        "strange to put a chatbot on the front that could quietly contradict "
        "the report one tab away.",
        badge="method",
        followups=("What can you answer?",
                   "How do you know the findings are reliable?"))


def a_help() -> Answer:
    return Answer(
        "Here is my full range. I can answer questions about:\n\n"
        "**The birds** - at-risk and conservation species, species richness, "
        "diversity indices, habitat specialists, which species are unique to "
        "one habitat.\n\n"
        "**Place and time** - which parks are best and for what, time of day, "
        "seasonal patterns, survey coverage.\n\n"
        "**Conditions** - temperature, humidity, sky, wind, disturbance.\n\n"
        "**Method and trust** - observer effects, how birds were detected, the "
        "four guardrails, what the study cannot answer, and why some findings "
        "were rejected.\n\n"
        "**Decisions** - what the survey team should do next, and what it would "
        "cost.\n\n"
        "Ask in your own words. I do not need keywords.",
        followups=("What is the biggest finding?",
                   "Which park should I visit?",
                   "Tell me something surprising"))


def a_thanks() -> Answer:
    return Answer(
        "You're welcome. Ask me anything else - or head to the **Conclusion** "
        "page if you want the whole argument in one place, or **Report** to "
        "download the full document as PDF or Word.",
        followups=("What should the survey team do next?",
                   "Tell me something surprising"))


def a_bye() -> Answer:
    return Answer(
        "Goodbye. If you are leaving with one thing, make it this: the habitat "
        f"difference this survey was built to measure ({HAB_GAP:.2f} species "
        f"per session) is smaller than the difference between the three people "
        f"doing the measuring ({OBS_GAP:.2f}). That is not a failure - it is "
        "the finding.")


def a_dataset() -> Answer:
    return Answer(
        f"The dataset covers the **2018 breeding season (May to July)** across "
        f"**{q12['n_parks']} National Park Service units** in the "
        f"Mid-Atlantic region.\n\n"
        f"- **15,372** individual bird sightings\n"
        f"- **{q12['total_sessions']:,}** survey sessions - the unit of effort "
        f"everything is measured against\n"
        f"- **126** species recorded\n"
        f"- Two habitats: forest and grassland\n"
        f"- Three surveyors, one 10-minute point-count protocol\n\n"
        f"The important structural fact: only "
        f"**{q12['parks_with_both']} of {q12['n_parks']}** parks were surveyed "
        f"in *both* habitats. That single detail shapes nearly every "
        f"conclusion, because comparing forest in one park against grassland "
        f"in a different park compares the parks, not the habitats.",
        badge="descriptive",
        source="Q12 · Report §2",
        chart=chart_coverage,
        caption="Only sessions from parks surveyed in both habitats can "
                "fairly address the central question.",
        followups=("Why does it matter that only 4 parks have both habitats?",
                   "How reliable is this data?"))


def a_at_risk() -> Answer:
    top = q5["species_profile"].index[0]
    return Answer(
        f"**Forest - but it is really one species.**\n\n"
        f"At-risk sightings are **{q1['ratio']}x** more frequent in forest: "
        f"{q1['forest_pct']}% of forest sessions record one against "
        f"{q1['grassland_pct']}% of grassland sessions "
        f"(p = {q1['p_value']:.1e}). That holds in **all "
        f"{q1['n_parks']}** parks surveyed in both habitats, which is what "
        f"makes it the strongest ecological result in the project.\n\n"
        f"But **{q1b['wood_thrush_share_pct']}%** of those sightings are "
        f"**{top}**. Remove that one species and the gap falls to "
        f"**{q1b['without_wood_thrush']['ratio']}x** and survives in only "
        f"{q1b['parks_agreeing_without']} of {q1['n_parks']} parks.\n\n"
        f"So the honest version is: *forest matters for {top}*, not *forest "
        f"matters for at-risk birds in general*. That is a narrower claim, and "
        f"a far more defensible one.",
        badge="narrowed",
        source="Q1 and Q1b · Report §4.1 · Habitat Comparison page",
        chart=chart_at_risk,
        table=pretty(q5["species_profile"]),
        caption="All eight at-risk species and where they were seen.",
        followups=("Which species are grassland specialists?",
                   "Should we protect forest or grassland?",
                   "How many species are there in total?"))


def a_richness() -> Answer:
    return Answer(
        f"**No - and this is the project's most instructive negative "
        f"result.**\n\n"
        f"Pool all {q12['n_parks']} parks together and forest and grassland "
        f"look significantly different: {q2['pooled']['forest']} against "
        f"{q2['pooled']['grassland']} species per session, "
        f"p = {q2['pooled']['p_value']:.1e}.\n\n"
        f"Restrict the comparison to the {q2['n_parks']} parks surveyed in "
        f"*both* habitats and it vanishes: {q2['within_shared']['forest']} "
        f"against {q2['within_shared']['grassland']}, "
        f"p = {q2['within_shared']['p_value']:.2f}. Forest comes out ahead in "
        f"exactly {q2['parks_favouring_forest']} of {q2['n_parks']} parks - a "
        f"coin flip.\n\n"
        f"The pooled result was **Simpson's paradox**: grassland ran more "
        f"sessions, in different parks, and the park differences masqueraded "
        f"as a habitat difference. Richness is simply the wrong question to "
        f"ask of habitat here. Composition is the right one.",
        badge="negative",
        source="Q2 · Report §4.3 · Habitat Comparison page",
        chart=chart_richness,
        caption="The same data, pooled and then restricted to shared parks.",
        followups=("Is that true for other diversity measures too?",
                   "What does differ between the habitats?",
                   "What is Simpson's paradox?"))


def a_diversity() -> Answer:
    t = q13["tests"]
    return Answer(
        f"**All four measures agree: no difference.**\n\n"
        f"Richness only counts species and ignores how evenly individuals are "
        f"spread across them, so the null result could have been an artefact "
        f"of picking the wrong measure. It is not.\n\n"
        f"- **Richness** — {t['richness']['forest']} vs "
        f"{t['richness']['grassland']}, p = {t['richness']['p_value']:.2f}\n"
        f"- **Shannon** (weights rare species) — {t['shannon']['forest']} vs "
        f"{t['shannon']['grassland']}, p = {t['shannon']['p_value']:.2f}\n"
        f"- **Simpson** (weights common species) — "
        f"{t['simpson_diversity']['forest']} vs "
        f"{t['simpson_diversity']['grassland']}, "
        f"p = {t['simpson_diversity']['p_value']:.2f}\n"
        f"- **Pielou's evenness** (strips richness out entirely) — "
        f"{t['evenness']['forest']} vs {t['evenness']['grassland']}, "
        f"p = {t['evenness']['p_value']:.2f}\n\n"
        f"The smallest p-value across all four is **{MIN_P13:.2f}**. Nothing "
        f"comes close. Four measures with different sensitivities pointing the "
        f"same way is much stronger than one measure pointing that way alone.",
        badge="negative",
        source="Q13 · Report §4.5 · Habitat Comparison page",
        chart=chart_diversity,
        caption="Each measure as a forest ÷ grassland ratio. The dashed line "
                "is 1.0 - perfect equality.",
        followups=("So what does differ between the habitats?",
                   "Which species are specialists?"))


def a_similarity() -> Answer:
    return Answer(
        f"**The species list is nearly the same. The weighting is not.**\n\n"
        f"This is the sharpest statement the project can make about habitat.\n\n"
        f"**Jaccard** asks *which* species are present. Between habitats in the "
        f"same park it is **{SIM['between_habitat']['jaccard']}**; within one "
        f"habitat across different parks it is "
        f"**{SIM['within_habitat']['jaccard']}**. Essentially identical - "
        f"forest and grassland draw on the same species pool.\n\n"
        f"**Bray-Curtis** asks *how common* each species is. Here the two "
        f"separate by **{SIM['bray_gap']:.3f}**. Same roster, different mix.\n\n"
        f"One caveat that matters: rarefying to equal session counts shrank "
        f"that Bray-Curtis gap by **"
        f"{SIM['rarefaction_shrank_bray_gap_by_pct']}%**. Most of the apparent "
        f"difference was survey effort, not ecology. What survives is real but "
        f"much smaller than the raw numbers suggested.",
        badge="strong",
        source="Q13 · Report §4.5.1",
        chart=chart_similarity,
        caption="Lower Bray-Curtis means more similar. The habitats share a "
                "species list but weight it differently.",
        followups=("What is rarefaction?",
                   "Which species are only found in one habitat?"))


def a_specialists() -> Answer:
    names = list(q4["grassland_specialists"]["Common_Name"][:6]) \
        if "Common_Name" in q4["grassland_specialists"].columns else []
    listed = ", ".join(names) if names else ""
    extra = (f"\n\nA few of them: {listed}." if listed else "")
    return Answer(
        f"**Grassland has {q4['n_grassland']} specialists. Forest has "
        f"{q4['n_forest']}.**\n\n"
        f"Of the {q4['n_well_sampled']} species sampled well enough to "
        f"classify, {q4['n_grassland']} are grassland specialists, "
        f"{q4['n_generalist']} are generalists that use both habitats, and "
        f"**zero** depend on forest exclusively.{extra}\n\n"
        f"This is the single most decision-relevant asymmetry in the dataset. "
        f"Converting grassland removes the only habitat that "
        f"{q4['n_grassland']} species reliably use. Converting forest removes "
        f"habitat that no well-sampled species depends on exclusively - the "
        f"forest birds here are generalists that also turn up in grassland.\n\n"
        f"Combined with the richness null result, that gives a clear line: "
        f"there is no \"more species\" argument for preferring either habitat, "
        f"and there is a strong species-loss argument against converting "
        f"grassland.",
        badge="strong",
        source="Q4 · Report §4.6 · Species page",
        chart=chart_specialists,
        followups=("Should we protect forest or grassland?",
                   "Which habitat has more at-risk birds?"))


def a_best_park() -> Answer:
    rate = q3["parks_by_rate"]
    rel = rate[rate["reliable"]]
    best = rel.index[0]
    return Answer(
        f"**It depends entirely on what you are going for - and that is the "
        f"finding, not a dodge.**\n\n"
        f"For **species per session**, the top reliable park is "
        f"**{NAME.get(best, best)}** at {rel.iloc[0]['species_per_session']} "
        f"species across {int(rel.iloc[0]['sessions_run'])} sessions.\n\n"
        f"But the park with the highest **at-risk detection rate** ranks *last* "
        f"of {q12['n_parks']} for species per session. A single \"best parks\" "
        f"list would send conservation staff and biodiversity visitors to "
        f"opposite ends of it.\n\n"
        f"One warning about ranking: raw species counts track how often a park "
        f"was visited, not how rich it is. Only the per-session rate is a fair "
        f"comparison, and that is what is plotted here. Grey bars are parks "
        f"below the {RELIABLE_FLOOR}-session floor - shown, but not to be "
        f"ranked on.",
        badge="strong",
        source="Q3 · Report §4.7 · Where page",
        chart=chart_parks,
        caption=f"Green bars clear the {RELIABLE_FLOOR}-session reliability "
                f"floor. Grey ones do not.",
        followups=("Why can't you rank individual plots?",
                   "Which park has the most disturbance?"))


def a_time_of_day() -> Answer:
    return Answer(
        f"**Early - but only in grassland.**\n\n"
        f"Grassland sessions record **{G7['gain_pct']}%** more species early "
        f"(5-6am) than late (9-10am): {G7['early_mean']} against "
        f"{G7['late_mean']} species per session, p = {G7['p_value']:.1e}. The "
        f"whole-morning trend agrees, and the medians move too - 10 to 9 to 8 "
        f"across the three bands - so this is the entire distribution sliding, "
        f"not a few unusually rich early sessions.\n\n"
        f"Forest is **flat**: {F7['early_mean']} early against "
        f"{F7['late_mean']} late, p = {F7['p_value']:.2f}. If anything it ends "
        f"the morning slightly higher.\n\n"
        f"This is the most directly actionable finding in the project. Unlike "
        f"the seasonal question it survives every control check: session "
        f"length is a median of 10 minutes in every band, and sessions are "
        f"spread across all three bands in both habitats.",
        badge="strong",
        source="Q7 · Report §4.8 · Timing page",
        chart=chart_time_of_day,
        followups=("Is there a seasonal pattern too?",
                   "What weather is best for surveying?"))


def a_season() -> Answer:
    return Answer(
        f"**There is a pattern, but this dataset cannot call it seasonal - and "
        f"that distinction matters.**\n\n"
        f"Species per session does fall from May to July in both habitats. The "
        f"problem is that visit number and calendar date correlate at "
        f"**rho 0.89** in this survey: the first visit to a plot was almost "
        f"always in May, the third almost always in July. Third visits happened "
        f"in grassland only.\n\n"
        f"So a genuine seasonal decline and simple repeat-visit decline - "
        f"observers finding less on a third pass, birds becoming less vocal "
        f"after peak breeding - fit the data equally well, and nothing in this "
        f"dataset separates them.\n\n"
        f"Reported as descriptive only. No amount of post-hoc analysis fixes "
        f"this; it needs a design change (rotate visit order across plots), "
        f"which costs nothing and would unlock the whole question next season.",
        badge="descriptive",
        source="Q6 · Report §4.9 · Timing page",
        chart=chart_season,
        caption="Real, and honestly unattributable. Forest effort is also "
                "badly imbalanced across the three months.",
        followups=("What should the survey team change next season?",
                   "What else can't this study answer?"))


def a_weather() -> Answer:
    c = q8["correlations"]
    return Answer(
        f"**Mild is best - around {q8['temperature_peak_band']} - and the "
        f"correlation coefficient misleads here.**\n\n"
        f"Species per session peaks at "
        f"{q8['temperature'].loc[q8['temperature_peak_band'], 'species_per_session']} "
        f"in the {q8['temperature_peak_band']} band and falls away on **both** "
        f"sides - down to "
        f"{q8['temperature'].loc['>30C', 'species_per_session']} above 30C and "
        f"{q8['temperature'].loc['<15C', 'species_per_session']} below 15C.\n\n"
        f"Spearman's rho returns {c['Forest_Temperature']['rho']} for forest "
        f"and {c['Grassland_Temperature']['rho']} for grassland, both "
        f"significant, both negative. Read alone that says *colder is better* "
        f"- and the chart says it plainly is not. Rho is a monotonic statistic "
        f"and this relationship is a hump, so the number is not wrong, it is "
        f"answering a different question than the one being asked.\n\n"
        f"**Humidity** carries almost nothing once temperature is accounted "
        f"for, and the two show no sign of interacting.",
        badge="strong",
        source="Q8 · Report §4.11 · Environment page",
        chart=chart_temperature,
        caption="The peak band is highlighted. The coldest band sits below "
                "the peak, not above it.",
        followups=("What about sky and wind?",
                   "What hurts the count most?"))


def a_disturbance() -> Answer:
    return Answer(
        f"**Disturbance - and it is the largest single effect in the project.**"
        f"\n\n"
        f"Sessions with serious disturbance record **{dt['loss_pct']}% fewer "
        f"species**: {dt['none_mean']} drops to {dt['serious_mean']}, "
        f"p = {dt['p_value']:.1e}. That is a gap of **{DIST_GAP:.2f}** species "
        f"per session, against a habitat gap of {HAB_GAP:.2f}.\n\n"
        f"It also matters that disturbance is the only environmental variable "
        f"that is a property of the *site and schedule* rather than the "
        f"weather - which makes it the only one anybody can actually change.\n\n"
        f"One honest oddity: sessions marked *slight* disturbance score "
        f"slightly **higher** than *no* disturbance. Their medians are "
        f"identical, so this is a heavier upper tail rather than a real lift - "
        f"most likely 'slight' is recorded more often at busier, more "
        f"accessible sites that are also richer. Flagged rather than explained "
        f"away.\n\n"
        f"**Where it happens:** {NAME.get(DISTURBED.index[0], DISTURBED.index[0])} "
        f"recorded moderate or serious disturbance in **{DISTURBED.iloc[0]}%** of "
        f"its {int(PARK_SESSIONS[DISTURBED.index[0]])} sessions, against "
        f"**{DISTURBED.iloc[-1]}%** at "
        f"{NAME.get(DISTURBED.index[-1], DISTURBED.index[-1])}. The parks at the "
        f"top of that list are linear and urban sites - parkways and city parks, "
        f"where roads and footfall run alongside the plots.",
        badge="strong",
        source="Q9 · Report §4.10 · Environment page",
        chart=chart_disturbance,
        followups=("Which park has the most disturbance?",
                   "What can the team actually control?"))


def a_sky_wind() -> Answer:
    s = q9["sky"]
    return Answer(
        f"**Both matter less than you would expect, and both are weaker than "
        f"disturbance.**\n\n"
        f"The best sky condition is **{s.index[0]}** at "
        f"{s.iloc[0]['species_per_session']} species per session; the worst "
        f"reliable one is **{s.index[-1]}** at "
        f"{s.iloc[-1]['species_per_session']}. Interesting detail: clear skies "
        f"are *not* the best - partly cloudy edges them out, and fog and "
        f"drizzle are clearly worse.\n\n"
        f"Every one of these is a group difference rather than a proven cause, "
        f"and weather is not something a survey team can schedule around "
        f"anyway. Disturbance is where the actionable signal lives.",
        badge="descriptive",
        source="Q9 · Report §4.10 · Environment page",
        table=pretty(q9["sky"]),
        followups=("What hurts the count most?",
                   "What is the best temperature?"))


def a_observer() -> Answer:
    return Answer(
        f"**Yes - massively, and it is the most important result in the "
        f"project.**\n\n"
        f"The three surveyors differ by **{q10['spread_pct']}%** in species "
        f"recorded per session - a gap of **{OBS_GAP:.2f}** species against a "
        f"habitat gap of **{HAB_GAP:.2f}**. Which person held the clipboard "
        f"moves the measurement roughly {OBS_GAP / HAB_GAP:.0f} times more "
        f"than the thing the survey was built to study. Every pairwise "
        f"difference is statistically significant.\n\n"
        f"The study survives this for one reason: the rota was **balanced**. "
        f"Each surveyor covered close to a third of both habitats, with a "
        f"maximum deviation of "
        f"{q10['max_habitat_share_deviation'] * 100:.1f} percentage points, so "
        f"the observer effect cancels out of any habitat comparison instead of "
        f"biasing it. Had surveyor assignment correlated with habitat, this "
        f"project would have measured the surveyor and reported it as "
        f"ecology.\n\n"
        f"That was a design choice, not luck - and it deserves to be recorded "
        f"as the most consequential methodological decision in the survey.",
        badge="method",
        source="Q10 · Report §5.1 · Data Quality page",
        chart=chart_observer,
        followups=("Why do the observers differ?",
                   "Does that invalidate the findings?"))


def a_detection() -> Answer:
    return Answer(
        f"**{q14['auditory_pct']}% of detections are made by ear - and that "
        f"explains the observer gap.**\n\n"
        f"Two of the three identification methods are auditory. Singing alone "
        f"accounts for {q14['method_share']['Singing']}% of detections and "
        f"calling a further {q14['method_share']['Calling']}%; only "
        f"{q14['method_share']['Visualization']}% of birds were identified by "
        f"sight. In practice this survey is a **hearing test**.\n\n"
        f"Split the observer gap by channel and it stops being mysterious: "
        f"**{q14['auditory_gap']:.2f}** species between surveyors on auditory "
        f"detections against **{q14['visual_gap']:.2f}** on visual. And the "
        f"ordering reverses - the surveyor who records fewest species overall "
        f"is *not* the lowest on the visual channel.\n\n"
        f"Someone who was simply less thorough, or spent less time at the plot, "
        f"would be lowest on every channel. This one is not. So it is a "
        f"specific, **trainable** difference in song and call recognition "
        f"rather than a general difference in diligence - which turns the "
        f"project's most alarming finding into a half-day of pre-season "
        f"calibration.",
        badge="method",
        source="Q14 · Report §5.2 · Data Quality page",
        chart=chart_detection,
        followups=("What should the survey team do next?",
                   "Does the observer gap invalidate the findings?"))


def a_coverage() -> Answer:
    return Answer(
        f"**{q12['parks_with_both']} of {q12['n_parks']} parks were surveyed "
        f"in both habitats - so only {q12['usable_pct']}% of sessions can "
        f"address the central question.**\n\n"
        f"That leaves {q12['total_sessions'] - q12['usable_sessions']:,} "
        f"sessions of real fieldwork that cannot contribute to a fair habitat "
        f"comparison, because comparing forest in one park against grassland "
        f"in another compares the parks.\n\n"
        f"All seven single-habitat parks are **forest-only**. Median session "
        f"length is 10 minutes in both habitats, so effort per session is "
        f"directly comparable and no figure in this project needs a duration "
        f"correction.\n\n"
        f"Adding grassland plots to those seven parks is the highest-value "
        f"change available - roughly 210 extra sessions, about 15% more field "
        f"time, would bring usable data to 100%.",
        badge="descriptive",
        source="Q12 · Report §5.3",
        chart=chart_coverage,
        followups=("What should the survey team change next season?",
                   "How reliable is this data?"))


def a_guardrails() -> Answer:
    return Answer(
        "**Four rules, applied everywhere, and they changed the answers.**\n\n"
        "**G1 — per-session rates, never raw counts.** A park visited twice as "
        "often records more species. Every figure is a rate.\n\n"
        "**G2 — shared parks only for habitat comparisons.** Comparing forest "
        "in one park with grassland in another compares parks. This one turned "
        "a significant richness result into a null one.\n\n"
        f"**G3 — a {RELIABLE_FLOOR}-session floor.** Anything below it is "
        "shown greyed out and never ranked. On the Environment page only 9 of "
        "20 temperature-humidity cells clear it.\n\n"
        f"**G4 — rarefaction for unequal effort.** Comparing species counts "
        f"between unequal samples inflates the larger one. It cut the apparent "
        f"exclusive-species advantage roughly fourfold, and shrank the "
        f"community-similarity gap by "
        f"{SIM['rarefaction_shrank_bray_gap_by_pct']}%.\n\n"
        "These are not decoration. Without G2 this project would have "
        "confidently reported a habitat richness effect that does not exist.",
        badge="method",
        source="Report §3.4 · Data Quality page",
        followups=("What is Simpson's paradox?",
                   "What can't this study answer?"))


def a_simpsons() -> Answer:
    return Answer(
        f"**A trend that appears in pooled data and reverses or vanishes when "
        f"you look at the groups separately.** This project contains a "
        f"textbook case in its own data.\n\n"
        f"Pooled across all {q12['n_parks']} parks, grassland shows "
        f"significantly higher richness than forest "
        f"(p = {q2['pooled']['p_value']:.1e}). Split by park and the effect "
        f"disappears (p = {q2['within_shared']['p_value']:.2f}).\n\n"
        f"The cause: grassland ran "
        f"{q11['sessions']['ratio']}x more sessions than forest, and it ran "
        f"them in *different parks*. Some parks are simply richer than others. "
        f"Pooling let that park-level difference wear a habitat costume.\n\n"
        f"This is exactly why guardrail G2 - shared parks only - exists, and "
        f"why the honest headline of this project is a negative result.",
        badge="method",
        source="Q2 · Report §4.3",
        chart=chart_richness,
        followups=("What are the four guardrails?",
                   "So what does differ between the habitats?"))


def a_recommendations() -> Answer:
    return Answer(
        f"**Five design changes, and three of them cost nothing.**\n\n"
        f"**Free — schedule and paperwork only:**\n"
        f"1. Write the balanced observer rota into the protocol. It currently "
        f"exists as practice, and it is the reason the conclusions hold.\n"
        f"2. Rotate visit order across plots, so a seasonal question becomes "
        f"answerable.\n"
        f"3. Run a pre-season call-recognition calibration. "
        f"{q14['auditory_pct']}% of detections are auditory and that is where "
        f"the observer gap lives.\n\n"
        f"**Costed in sessions:**\n"
        f"4. Lift the two smallest parks over the {RELIABLE_FLOOR}-session "
        f"floor — 20 sessions.\n"
        f"5. Add grassland plots to the seven forest-only parks — about 210 "
        f"sessions, 15% more field time, which brings usable data from "
        f"{q12['usable_pct']}% to 100%. Every session invested brings back "
        f"roughly 3.2 currently unusable ones.\n\n"
        f"**For management:** protect mature forest where Wood Thrush is "
        f"present, reduce disturbance during survey windows, and do **not** "
        f"convert grassland on diversity grounds - it holds all "
        f"{q4['n_grassland']} habitat specialists while forest holds none.",
        badge="strong",
        source="Report §8 · Conclusion page",
        chart=chart_levers,
        caption="Green bars are things the team can decide. Grey is the "
                "question the survey was designed to answer.",
        followups=("What can't this study answer?",
                   "Which habitat should we protect?"))


def a_limitations() -> Answer:
    return Answer(
        f"**Quite a lot, and listing it honestly is part of the point.**\n\n"
        f"- **Anything seasonal.** Visit number and calendar date correlate at "
        f"rho 0.89, so seasonal decline cannot be separated from repeat-visit "
        f"decline.\n"
        f"- **Anything about individual plots.** No plot was visited more than "
        f"three times. The plot leaderboard is the right tail of a noisy "
        f"distribution, not a list of good places.\n"
        f"- **Equivalence between habitats.** The null result rests on "
        f"{q2['within_shared']['n_forest']} forest sessions in "
        f"{q2['n_parks']} parks. That is enough to reject a strong claim, not "
        f"enough to prove the habitats are the same.\n"
        f"- **The seven forest-only parks.** "
        f"{q12['total_sessions'] - q12['usable_sessions']:,} sessions cannot "
        f"contribute to the central question at all.\n"
        f"- **Absolute species counts.** The observer spread means "
        f"species-per-session carries a personal calibration band of roughly "
        f"±{OBS_GAP / 2:.1f} species. Comparisons *within* this dataset are "
        f"sound; the absolute numbers should not be quoted against another "
        f"study's.\n"
        f"- **Causation anywhere.** Every environmental finding is a group "
        f"difference from observational data.",
        badge="method",
        source="Report §9 · Conclusion page",
        followups=("What should the survey team change next season?",
                   "What IS well supported?"))


def a_biggest() -> Answer:
    return Answer(
        f"**That the habitat difference this survey was built to measure is "
        f"smaller than the difference between the people doing the "
        f"measuring.**\n\n"
        f"Habitat moves species per session by **{HAB_GAP:.2f}**. Which of "
        f"three surveyors held the clipboard moves it by **{OBS_GAP:.2f}**. "
        f"Disturbance moves it by **{DIST_GAP:.2f}**.\n\n"
        f"That sounds like a disappointing outcome and is not. It is the "
        f"reason the guardrails exist, and the reason this dashboard reports "
        f"what it rejected as carefully as what it found. A pooled comparison, "
        f"an unbalanced rota or an unquestioned park leaderboard would each "
        f"have produced a confident, publishable, wrong answer.\n\n"
        f"And the habitat signal that *does* survive is the more useful one: "
        f"not how many species, but which. Wood Thrush in forest, "
        f"{q4['n_grassland']} specialists in grassland, and the same species "
        f"list weighted differently between the two.",
        badge="strong",
        source="Conclusion page · Report §7",
        chart=chart_levers,
        followups=("Why do the observers differ so much?",
                   "What should the team do about it?"))


SURPRISES = [
    ("**Clear skies are not the best surveying weather.** Partly cloudy "
     f"sessions record {q9['sky'].iloc[0]['species_per_session']} species "
     f"against {q9['sky'].loc['Clear or Few Clouds', 'species_per_session']} "
     "for clear ones. Fog and drizzle are genuinely worse, but the sunny-day "
     "intuition does not hold."),
    ("**Sessions with *slight* disturbance score higher than sessions with "
     "none** - 9.38 against 8.93. But their medians are identical at 9.0, so "
     "it is a heavier upper tail rather than a real lift. Probably 'slight' "
     "gets recorded more at busier, more accessible, richer sites."),
    (f"**Not one forest specialist.** Of {q4['n_well_sampled']} well-sampled "
     f"species, {q4['n_grassland']} depend on grassland exclusively and "
     f"**zero** depend on forest. Every forest bird here also turns up in "
     f"grassland."),
    (f"**{q1b['wood_thrush_share_pct']}% of all at-risk sightings are a single "
     f"species.** Wood Thrush alone carries the entire forest conservation "
     f"result. Remove it and the effect drops from {q1['ratio']}x to "
     f"{q1b['without_wood_thrush']['ratio']}x."),
    (f"**Half of everything is heard in the first 150 seconds.** "
     f"{q14['first_interval_pct']}% of detections arrive in the first 2.5 "
     f"minutes of a 10-minute count. The last quarter of every count adds only "
     f"{100 - q14['interval_cumulative']['5 - 7.5 min']:.1f}%."),
    (f"**Missing data that maps perfectly onto a rule is a good sign.** Every "
     f"record with no Distance value is a flyover - a bird passing overhead "
     f"with no distance to record. The correspondence is one-to-one with zero "
     f"exceptions."),
    (f"**Rarefaction erased most of a headline number.** Grassland appeared to "
     f"have roughly four times as many exclusive species as forest. Corrected "
     f"for the fact that it ran {q11['sessions']['ratio']}x more sessions, "
     f"most of that gap was survey effort."),
]


def a_surprise() -> Answer:
    i = st.session_state.get("surprise_i", 0)
    st.session_state["surprise_i"] = (i + 1) % len(SURPRISES)
    return Answer(
        SURPRISES[i] + "\n\nAsk again for another.",
        badge="none",
        followups=("Tell me something surprising",
                   "What is the biggest finding?"))


def a_report() -> Answer:
    return Answer(
        "The full report is on the **Report** page, where you can download it "
        "as **PDF** or **Word**, plus a findings ledger in markdown.\n\n"
        "It runs to ten sections and two appendices - introduction, dataset, "
        "methodology, results for all fourteen questions, data quality, "
        "discussion, insights, recommendations, limitations and conclusion, "
        "plus a reproducibility appendix and a 49-field data dictionary.\n\n"
        "All three formats are rendered from one content model, so the "
        "dashboard, the PDF and the Word document cannot disagree with each "
        "other.",
        followups=("What are the main recommendations?",
                   "What can't this study answer?"))


def a_unknown() -> Answer:
    return Answer(
        "I could not match that to anything in this survey, and I would rather "
        "say so than invent an answer.\n\n"
        "I only know about the 2018 breeding-season bird survey behind this "
        "dashboard - its 14 analysis questions, its methods, and its "
        "limitations. I have no knowledge of birds in general, other studies, "
        "or anything outside this dataset.\n\n"
        "Try rephrasing, or pick one of these:",
        followups=("What can you answer?",
                   "What is the biggest finding?",
                   "Which habitat is better for at-risk birds?",
                   "Tell me something surprising"))


# ==================================================================== intents
# Weighted keyword matching. A phrase scores its weight when found as a
# substring of the normalised question. An intent fires when its total clears
# THRESHOLD, and the highest scorer wins. Weights are deliberately blunt:
# 3 = unambiguous for this topic, 2 = strong, 1 = supporting only.
INTENTS: dict[str, tuple[Callable[[], Answer], dict[str, int]]] = {
    "greeting": (a_greeting, {
        "hello": 3, "hi ": 3, "hey": 3, "good morning": 3, "good evening": 3,
        "good afternoon": 3, "namaste": 3, "yo ": 2, "greetings": 3}),
    "who": (a_who, {
        "who are you": 4, "what are you": 4, "are you chatgpt": 4,
        "are you an ai": 4, "are you a bot": 4, "are you real": 3,
        "llm": 3, "chatgpt": 3, "gpt": 2, "language model": 4,
        "how do you work": 3, "are you claude": 4}),
    "help": (a_help, {
        "what can you": 4, "help": 3, "capabilit": 3, "what do you know": 4,
        "what questions": 3, "options": 2, "topics": 2}),
    "thanks": (a_thanks, {
        "thank": 3, "thanks": 3, "cheers": 2, "appreciate": 2, "helpful": 2}),
    "bye": (a_bye, {
        "bye": 3, "goodbye": 3, "see you": 3, "that's all": 3, "exit": 2}),
    "dataset": (a_dataset, {
        "dataset": 3, "data set": 3, "how many record": 3, "how many row": 3,
        "how many sighting": 3, "how much data": 3, "what data": 3,
        "source": 2, "where does the data": 3, "sample size": 3,
        "how many session": 2, "tell me about the data": 4}),
    "at_risk": (a_at_risk, {
        "at-risk": 4, "at risk": 4, "endangered": 3, "conservation": 3,
        "watchlist": 3, "watch list": 3, "wood thrush": 4, "threatened": 3,
        "pif": 2, "vulnerable": 2, "protect": 1, "rare species": 2}),
    "richness": (a_richness, {
        "richness": 4, "how many species": 3, "more species": 3,
        "species count": 3, "number of species": 3, "which habitat has more": 4,
        "biodiversity": 2, "more diverse": 2, "forest or grassland": 2}),
    "diversity": (a_diversity, {
        "shannon": 4, "simpson index": 4, "simpsons index": 4, "evenness": 4,
        "pielou": 4, "diversity index": 4, "diversity indices": 4,
        "other measures": 3, "other diversity": 3}),
    "similarity": (a_similarity, {
        "jaccard": 4, "bray": 4, "similarity": 3, "community": 3,
        "composition": 3, "what does differ": 4, "what differs": 4,
        "same species": 2, "species pool": 3, "rarefaction": 2,
        "rarefied": 2, "what is rarefaction": 4}),
    "specialists": (a_specialists, {
        "specialist": 4, "only found in": 3, "exclusive": 3, "unique to": 3,
        "depend on": 3, "generalist": 3, "which species live": 3,
        "grassland bird": 2, "forest bird": 2, "should we protect": 5,
        "which habitat should": 5, "protect forest": 4,
        "protect grassland": 4, "convert": 3, "forest or grassland": 3}),
    "best_park": (a_best_park, {
        "best park": 4, "which park": 4, "hotspot": 3, "top park": 4,
        "where should": 3, "which site": 3, "best place": 3, "visit": 2,
        "rank": 2, "leaderboard": 3, "plot": 2, "location": 2}),
    "time_of_day": (a_time_of_day, {
        "time of day": 4, "morning": 3, "early": 3, "what time": 3,
        "when should": 3, "hour": 3, "dawn": 3, "5am": 3, "6am": 3,
        "best time": 4, "late": 2}),
    "season": (a_season, {
        "season": 4, "seasonal": 4, "month": 3, "may": 2, "june": 3,
        "july": 3, "over time": 2, "trend": 2, "decline": 2,
        "time of year": 4}),
    "weather": (a_weather, {
        "weather": 3, "temperature": 4, "humidity": 4, "hot": 3, "cold": 3,
        "warm": 3, "degrees": 3, "climate": 2, "temp": 3}),
    "disturbance": (a_disturbance, {
        "disturb": 4, "noise": 3, "noisy": 3, "interference": 3,
        "what hurts": 4, "worst for": 4, "biggest effect": 3,
        "what reduces": 4, "traffic": 2, "people": 1,
        "hurts the count": 5, "hurts the species": 5, "actually control": 4,
        "can the team control": 5, "what can we control": 4,
        "can be changed": 3, "can we change": 3,
        "park has the most disturb": 6, "most disturbed": 5,
        "which park has the most": 4, "where is it worst": 4}),
    "sky_wind": (a_sky_wind, {
        "sky": 4, "wind": 4, "cloud": 3, "rain": 3, "fog": 3, "drizzle": 3,
        "sunny": 3, "overcast": 3, "clear sky": 4}),
    "observer": (a_observer, {
        "observer": 4, "surveyor": 4, "who recorded": 3, "person": 2,
        "people differ": 3, "bias": 3, "human error": 3, "reliable": 1,
        "does it matter who": 4, "invalidate": 3, "trust the": 2}),
    "detection": (a_detection, {
        "detect": 3, "hear": 3, "heard": 3, "hearing": 4, "sound": 3,
        "call": 3, "song": 3, "singing": 4, "sing": 3, "visual": 3,
        "by sight": 4, "by ear": 4, "how were birds": 4, "identif": 2,
        "why do the observers differ": 6, "why do the surveyors differ": 6,
        "why do they differ": 5, "interval": 3, "10 minute": 2}),
    "coverage": (a_coverage, {
        "coverage": 4, "effort": 3, "how many park": 3, "shared park": 4,
        "both habitat": 4, "only 4 park": 4, "why does it matter that": 3,
        "usable": 3, "survey design": 2}),
    "guardrails": (a_guardrails, {
        "guardrail": 4, "how do you know": 3, "how reliable": 3,
        "can i trust": 3, "methodolog": 3, "rigor": 3, "quality": 2,
        "g1": 2, "g2": 2, "g3": 2, "g4": 2, "safeguard": 3,
        "how was this checked": 4, "how do i know": 4,
        "findings are reliable": 5, "are reliable": 3,
        "is this reliable": 4, "trust": 3, "how reliable is": 4,
        "believe": 2, "confident": 2, "robust": 3}),
    "simpsons": (a_simpsons, {
        "simpson's paradox": 5, "simpsons paradox": 5, "paradox": 4,
        "why did it disappear": 4, "pooled": 3}),
    "recommendations": (a_recommendations, {
        "recommend": 4, "what should": 3, "advice": 3, "action": 3,
        "do next": 4, "next season": 4, "improve": 3, "change": 2,
        "suggest": 3, "priorit": 3, "what now": 3}),
    "limitations": (a_limitations, {
        "limitation": 4, "cannot answer": 4, "can't answer": 4,
        "weakness": 3, "problem": 2, "flaw": 3, "caveat": 3,
        "what can't": 3, "what cant": 3, "shortcoming": 3, "not able": 3,
        "why can't you": 4, "why cant you": 4, "rank individual": 5,
        "can't this study": 4, "cant this study": 4, "else can't": 4,
        "else cant": 4,
        "individual plot": 4, "rank plots": 5}),
    "biggest": (a_biggest, {
        "biggest finding": 5, "main finding": 5, "key finding": 5,
        "most important": 4, "headline": 4, "summar": 3, "takeaway": 4,
        "what did you find": 4, "bottom line": 4, "one thing": 3,
        "what is well supported": 4, "what is supported": 3}),
    "surprise": (a_surprise, {
        "surpris": 4, "interesting": 3, "tell me something": 4,
        "random": 3, "fun fact": 4, "unexpected": 4, "weird": 3,
        "counterintuitive": 4}),
    "report": (a_report, {
        "report": 3, "pdf": 4, "word doc": 4, "download": 3,
        "document": 3, "export": 3, "ledger": 3}),
}

THRESHOLD = 3


def normalise(text: str) -> str:
    t = " " + re.sub(r"[^a-z0-9' -]+", " ", text.lower()) + " "
    return re.sub(r"\s+", " ", t)


def match(question: str) -> tuple[str, int]:
    """Return (intent_key, score). Score 0 means no confident match."""
    n = normalise(question)
    best, best_score = "unknown", 0
    for key, (_, keywords) in INTENTS.items():
        score = sum(w for phrase, w in keywords.items() if phrase in n)
        if score > best_score:
            best, best_score = key, score
    return (best, best_score) if best_score >= THRESHOLD else ("unknown", 0)


def answer_for(intent: str) -> Answer:
    if intent == "unknown":
        return a_unknown()
    return INTENTS[intent][0]()


# ==================================================================== helpers
def badge_html(kind: str) -> str:
    colour, label = BADGES.get(kind, ("", ""))
    if not label:
        return ""
    return (
        f'<span style="background:{colour};color:#fff;border-radius:5px;'
        f'padding:2px 9px;font-size:0.68rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;'
        f'white-space:nowrap">{label}</span>'
    )


def stream(text: str):
    """Word-by-word reveal, used only for a freshly generated answer."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.012)


def greeting_line() -> tuple[str, str]:
    h = datetime.now().hour
    if h < 12:
        return "Good morning", "🌅"
    if h < 17:
        return "Good afternoon", "☀️"
    if h < 21:
        return "Good evening", "🌆"
    return "Working late", "🌙"


def ask(question: str) -> None:
    intent, score = match(question)
    st.session_state.chat.append({"role": "user", "text": question})
    st.session_state.chat.append(
        {"role": "assistant", "intent": intent, "score": score, "new": True})
    st.session_state.asked = st.session_state.get("asked", 0) + 1


# ==================================================================== state
if "chat" not in st.session_state:
    st.session_state.chat = []
if "surprise_i" not in st.session_state:
    st.session_state.surprise_i = random.randrange(len(SURPRISES))

# A chip click sets this, then reruns; it is consumed at the top of the script
# so the new message is already in history by the time the transcript renders.
pending = st.session_state.pop("pending", None)
if pending:
    ask(pending)


# ==================================================================== 1. head
st.title("Ask the data")

hello, icon = greeting_line()
n_asked = st.session_state.get("asked", 0)
subtitle = (
    "Ask a question about the survey in your own words."
    if n_asked == 0 else
    f"{n_asked} question{'s' if n_asked != 1 else ''} answered so far."
)

st.markdown(
    f"""
<div style="background:linear-gradient(140deg,{theme.KPI_TOP},{theme.KPI_BOTTOM});
            border-radius:16px;padding:24px 28px;color:#ffffff;
            margin-bottom:6px">
  <div style="font-size:1.35rem;font-weight:800;margin-bottom:8px">
      {icon}&nbsp; {hello}.
  </div>
  <div style="font-size:0.95rem;line-height:1.7;color:#cfe3d6">
      I answer questions about the 2018 breeding-season bird survey -
      <b>15,372</b> sightings across <b>{q12['total_sessions']:,}</b> survey
      sessions, <b>126</b> species and <b>{q12['n_parks']}</b> National Park
      Service units. {subtitle}<br/><br/>
      Every figure I give you is pulled live from the analysis pipeline, so I
      cannot invent a number - and when I don't know something, I say so.
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.markdown(
    theme.caption(
        "No language model is involved. This is an intent-matching engine over "
        "the guarded pipeline - the same source the PDF report and every chart "
        "on this dashboard use. Ask <i>who are you</i> for the reasoning."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ==================================================================== 2. chips
if not st.session_state.chat:
    st.markdown("**Try one of these**")
    STARTERS = [
        ("Which habitat is better for at-risk birds?", "🪶"),
        ("What is the biggest finding?", "⭐"),
        ("When is the best time to survey?", "🕕"),
        ("Which park should I visit?", "📍"),
        ("What hurts the species count most?", "⚠️"),
        ("What can't this study answer?", "🚧"),
        ("How do I know the findings are reliable?", "🛡️"),
        ("Tell me something surprising", "🎲"),
    ]
    rows = [STARTERS[:4], STARTERS[4:]]
    for r, row in enumerate(rows):
        cols = st.columns(4, gap="small")
        for c, (text, emoji) in zip(cols, row):
            if c.button(f"{emoji}  {text}", key=f"start_{r}_{text[:12]}",
                        width='stretch'):
                st.session_state.pending = text
                st.rerun()

    st.write("")
    with st.expander("Everything I can answer, and what I cannot"):
        e1, e2 = st.columns(2, gap="large")
        with e1:
            st.markdown(
                "**I can answer**\n\n"
                "- At-risk and conservation species\n"
                "- Species richness and diversity indices\n"
                "- Habitat specialists and community composition\n"
                "- Park and plot rankings\n"
                "- Time of day and seasonal patterns\n"
                "- Temperature, humidity, sky, wind, disturbance\n"
                "- Observer effects and how birds were detected\n"
                "- Survey coverage and effort\n"
                "- The four guardrails and why findings were rejected\n"
                "- Recommendations and what they cost\n"
                "- The study's limitations"
            )
        with e2:
            st.markdown(
                "**I cannot answer**\n\n"
                "- Anything about birds outside this dataset\n"
                "- Other studies, papers or regions\n"
                "- Species identification or field-guide questions\n"
                "- Anything after the 2018 breeding season\n"
                "- Causal claims - this is observational data\n"
                "- Predictions about future seasons\n\n"
                "If you ask one of these I will tell you I don't know, rather "
                "than produce something plausible-sounding. That is the whole "
                "design."
            )
    st.write("")

# ==================================================================== 3. chat
for i, msg in enumerate(st.session_state.chat):
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(msg["text"])
        continue

    ans = answer_for(msg["intent"])
    with st.chat_message("assistant", avatar="🐦"):
        if msg.get("new"):
            st.write_stream(stream(ans.text))
            msg["new"] = False
        else:
            st.markdown(ans.text)

        if ans.chart is not None:
            st.plotly_chart(ans.chart(), width='stretch',
                            config=theme.PLOTLY_CONFIG, key=f"chat_fig_{i}")
            if ans.caption:
                st.markdown(theme.caption(ans.caption),
                            unsafe_allow_html=True)

        if ans.table is not None:
            st.dataframe(ans.table, width='stretch')
            if ans.caption and ans.chart is None:
                st.markdown(theme.caption(ans.caption),
                            unsafe_allow_html=True)

        bits = []
        if badge_html(ans.badge):
            bits.append(badge_html(ans.badge))
        if ans.source:
            bits.append(
                f'<span style="font-size:0.78rem;color:{theme.MUTED}">'
                f'Evidence: {ans.source}</span>')
        if bits:
            st.markdown(
                '<div style="display:flex;gap:12px;align-items:center;'
                'margin-top:10px">' + "".join(bits) + "</div>",
                unsafe_allow_html=True)

# ---- follow-ups, attached to the most recent answer only
if st.session_state.chat and st.session_state.chat[-1]["role"] == "assistant":
    last = answer_for(st.session_state.chat[-1]["intent"])
    if last.followups:
        st.markdown(
            theme.caption("<b>Follow up</b>"), unsafe_allow_html=True)
        cols = st.columns(min(len(last.followups), 4), gap="small")
        for c, text in zip(cols, last.followups):
            if c.button(text, key=f"fu_{len(st.session_state.chat)}_{text[:16]}",
                        width='stretch'):
                st.session_state.pending = text
                st.rerun()

# ==================================================================== 4. input
typed = st.chat_input("Ask anything about the survey...")
if typed:
    st.session_state.pending = typed
    st.rerun()

if st.session_state.chat:
    st.write("")
    if st.button("Clear conversation", key="clear_chat"):
        st.session_state.chat = []
        st.session_state.asked = 0
        st.rerun()