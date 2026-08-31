"""
Conclusion - what to do about the findings.

The Report page records what was found. This page answers the next question:
so what. It is decision-oriented rather than evidence-oriented, and it is
deliberately willing to say "do nothing" where the evidence does not support
acting.

Layout, top to bottom:
  1. title
  2. what we now know - seven conclusions, each with a confidence rating and
     a pointer to the page and report section it comes from
  3. the levers chart - every effect the project can act on, in the same
     units, against the one it was designed to measure
  4. recommendations for management - what to do with the parks
  5. recommendations for survey design - what to change next season
  6. what each design change costs, in sessions, and what it returns
  7. the study this one could not be
  8. the single thing worth remembering

Every number on this page is read from the guarded analysis pipeline. The two
charts are the only ones in the project that mix questions together, because a
decision has to weigh findings against each other rather than read them one at
a time.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q1, q1b, q2, q4 = res["q1"], res["q1b"], res["q2"], res["q4"]
q7, q9, q10 = res["q7"], res["q9"], res["q10"]
q11, q12, q13, q14 = res["q11"], res["q12"], res["q13"], res["q14"]
sessions = da.sessions()
coords = da.park_coordinates()
NAME = dict(zip(coords["Admin_Unit_Code"], coords["park_name"]))

dt = q9["disturbance_test"]
obs = q10["per_observer"]["species_per_session"]
obs_gap = obs.max() - obs.min()
hab_gap = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])
g7 = q7["early_vs_late"]["Grassland"]
tod_gap = g7["early_mean"] - g7["late_mean"]
sim = q13["similarity"]
min_p13 = min(t["p_value"] for t in q13["tests"].values())

RELIABLE_FLOOR = 30
eff = q12["by_park"]
single = eff[~eff["both_habitats"]]
unusable = int(single["total"].sum())
low = eff[eff["total"] < RELIABLE_FLOOR]
floor_cost = int((RELIABLE_FLOOR - low["total"]).sum())

# Costing the habitat-pairing recommendation. The assumption is stated on the
# page rather than buried here: enough grassland sessions in each forest-only
# park to clear the same 30-session floor the rest of the dashboard uses.
pair_cost = RELIABLE_FLOOR * len(single)
pair_return = unusable / pair_cost
pair_pct = pair_cost / q12["total_sessions"] * 100

CONF = {
    "strong": (theme.FOREST, "Strong"),
    "narrowed": (theme.GRASSLAND, "Strong, narrowed"),
    "solid": (theme.SEQUENTIAL[4], "Solid"),
    "negative": (theme.AT_RISK, "Negative result"),
}


def conf(kind: str) -> str:
    colour, label = CONF[kind]
    return (
        f'<span style="background:{colour};color:#fff;border-radius:5px;'
        f'padding:2px 9px;font-size:0.7rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.05em;'
        f'white-space:nowrap">{label}</span>'
    )


def card(title: str, body: str, tag: str = "", accent: str = "",
         source: str = "") -> str:
    """A recommendation card. `source` traces it back to the evidence."""
    accent = accent or theme.FOREST
    tag_html = (
        f'<div style="font-size:0.7rem;font-weight:700;color:{accent};'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">'
        f'{tag}</div>' if tag else ""
    )
    src_html = (
        f'<div style="margin-top:12px;padding-top:10px;'
        f'border-top:1px solid {theme.BORDER};font-size:0.78rem;'
        f'color:{theme.MUTED}">Evidence: {source}</div>' if source else ""
    )
    return f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-left:4px solid {accent};border-radius:12px;
            padding:18px 20px;margin-bottom:14px;height:100%">
  {tag_html}
  <div style="font-weight:800;color:{theme.INK};font-size:1rem;
              line-height:1.4;margin-bottom:8px">{title}</div>
  <div style="font-size:0.89rem;color:{theme.INK2};line-height:1.7">{body}</div>
  {src_html}
</div>
"""


# ------------------------------------------------------------------ 1. title
st.title("Conclusion")
st.markdown(
    theme.caption(
        "The Report page records what was found. This page is about what to do "
        "with it - including where the honest recommendation is to change "
        "nothing. Every conclusion carries a confidence rating and a pointer "
        "back to the evidence."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. know
st.subheader("What we now know")

CONCLUSIONS = [
    ("narrowed",
     "Forest matters for Wood Thrush, not for at-risk birds in general",
     f"At-risk sightings are {q1['ratio']}x more frequent in forest "
     f"({q1['forest_pct']}% vs {q1['grassland_pct']}%, p = "
     f"{q1['p_value']:.1e}), holding in all {q1['n_parks']} shared parks. But "
     f"{q1b['wood_thrush_share_pct']}% of those sightings are Wood Thrush, and "
     f"without it the gap drops to {q1b['without_wood_thrush']['ratio']}x and "
     f"survives in only {q1b['parks_agreeing_without']} of {q1['n_parks']} "
     f"parks. Act on this as a single-species result.",
     "Habitat Comparison page &middot; Report &sect;4.1"),

    ("strong",
     "Grassland is irreplaceable; forest is not the only option for its birds",
     f"{q4['n_grassland']} of {q4['n_well_sampled']} well-sampled species are "
     f"grassland specialists. <b>Zero</b> are forest specialists - forest birds "
     f"here are generalists that also use grassland. Converting grassland "
     f"removes habitat that {q4['n_grassland']} species depend on; converting "
     f"forest removes habitat that no well-sampled species depends on "
     f"exclusively.",
     "Species page &middot; Report &sect;4.6"),

    ("strong",
     "Survey conditions cost more species than habitat does",
     f"Serious disturbance costs {dt['loss_pct']}% of recorded species "
     f"({dt['none_mean']} to {dt['serious_mean']}, p = {dt['p_value']:.1e}) - "
     f"a gap of {dt['none_mean'] - dt['serious_mean']:.2f} species per session "
     f"against a habitat gap of {hab_gap:.2f}. Timing and conditions are "
     f"levers; habitat, for richness, is not.",
     "Environment page &middot; Report &sect;4.10"),

    ("strong",
     "The surveyor is a bigger variable than anything being surveyed",
     f"A {q10['spread_pct']}% spread between three people, consistent in every "
     f"park, every pairwise difference significant. The study survives only "
     f"because the rota was balanced to within "
     f"{q10['max_habitat_share_deviation'] * 100:.1f} percentage points across "
     f"habitats. This is a result about method that outranks every result "
     f"about birds.",
     "Data Quality page &middot; Report &sect;5.1"),

    ("strong",
     "That surveyor gap is a hearing gap - and hearing can be trained",
     f"{q14['auditory_pct']}% of all detections are made by ear, so the survey "
     f"is in practice a hearing test. The between-surveyor gap is "
     f"{q14['auditory_gap']:.2f} species on auditory detections against "
     f"{q14['visual_gap']:.2f} on visual, and the surveyor who records fewest "
     f"species overall is <b>not</b> the lowest on the visual channel. Someone "
     f"who was simply less thorough would be lowest on every channel. This is "
     f"a specific, trainable difference in song and call recognition - which "
     f"turns the previous conclusion from a caveat into something fixable.",
     "Data Quality page &middot; Report &sect;5.2"),

    ("negative",
     "Habitat does not determine how many species you will see",
     f"Pooled, forest and grassland differ significantly "
     f"(p = {q2['pooled']['p_value']:.1e}). Within the "
     f"{q2['n_parks']} parks surveyed in both, they do not "
     f"(p = {q2['within_shared']['p_value']:.2f}), and forest wins in exactly "
     f"{q2['parks_favouring_forest']} of {q2['n_parks']}. The first number was "
     f"an artefact of which parks were surveyed how often.",
     "Habitat Comparison page &middot; Report &sect;4.3"),

    ("negative",
     "And that null result is not an artefact of measuring the wrong thing",
     f"Richness counts species and ignores how evenly individuals are spread "
     f"across them, so the null result above could have been an artefact of "
     f"the chosen measure. It is not. Shannon, Simpson and Pielou's evenness "
     f"all agree with richness, and the smallest p-value across all four is "
     f"{min_p13:.2f}. What <i>does</i> differ is the weighting: rarefied "
     f"community similarity puts Jaccard - which species are present - at "
     f"{sim['between_habitat']['jaccard']} between habitats against "
     f"{sim['within_habitat']['jaccard']} within one, essentially the same "
     f"species list, while Bray-Curtis - how common each one is - separates "
     f"them by {sim['bray_gap']:.3f}. Same roster, different mix.",
     "Habitat Comparison page &middot; Report &sect;4.5"),
]

for kind, title, body, source in CONCLUSIONS:
    st.markdown(
        f'<div style="display:flex;gap:12px;align-items:flex-start;'
        f'margin-bottom:6px">'
        f'<div style="flex:1;font-weight:800;color:{theme.INK};'
        f'font-size:1.02rem;line-height:1.4">{title}</div>{conf(kind)}</div>'
        f'<div style="font-size:0.9rem;color:{theme.INK2};line-height:1.7">'
        f'{body}</div>'
        f'<div style="font-size:0.78rem;color:{theme.MUTED};margin-top:8px;'
        f'padding-bottom:16px;border-bottom:1px solid {theme.BORDER};'
        f'margin-bottom:16px">Evidence: {source}</div>',
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. levers
st.subheader("What can actually be changed")

LEVERS = [
    ("Avoid serious disturbance", dt["none_mean"] - dt["serious_mean"], True),
    ("Train surveyors on calls", q14["auditory_gap"], True),
    ("Survey grassland early", tod_gap, True),
    ("Which surveyor is on visual", q14["visual_gap"], False),
    ("Forest vs grassland", hab_gap, False),
]

l1, l2 = st.columns([0.58, 0.42], gap="large")

with l1:
    labels = [n for n, _, _ in LEVERS][::-1]
    values = [v for _, v, _ in LEVERS][::-1]
    acts = [a for _, _, a in LEVERS][::-1]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=[theme.FOREST if a else theme.MUTED for a in acts],
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
        hovertemplate="%{y}<br>%{x:.2f} species per session<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="difference in species per session",
        **theme.plotly_layout(height=340, showlegend=False),
    )
    fig.update_xaxes(range=[0, max(values) * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Green bars are things a park manager or survey coordinator can "
            "decide. Grey bars are not levers. All five are measured in the "
            "same units - species recorded per 10-minute session - so they can "
            "be compared directly."
        ),
        unsafe_allow_html=True,
    )

with l2:
    st.markdown(
        theme.guardrail_banner(
            f"<b>The smallest bar is the one the study was built to "
            f"measure.</b> Habitat moves species per session by "
            f"{hab_gap:.2f}; disturbance moves it by "
            f"{dt['none_mean'] - dt['serious_mean']:.2f} and ear-training by "
            f"{q14['auditory_gap']:.2f}. Deliberately no ratio is quoted "
            f"here: the habitat figure is close enough to zero, and far "
            f"enough from significance, that dividing by it would produce an "
            f"impressive multiple with no stability behind it. The ordering "
            f"is the finding. Every practical gain available to this survey "
            f"lies in how it is run, not in where it is run."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            "This is the only chart in the project that puts different "
            "questions on one axis. It is here because a decision has to weigh "
            "findings against each other, whereas the analysis pages "
            "deliberately keep them apart. Two caveats travel with it: the "
            "disturbance and time-of-day bars are group differences rather "
            "than proven causes, and the habitat bar is a difference that "
            "failed its significance test - it is plotted at its measured "
            "size, which is close to zero, not at zero."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. mgmt
st.subheader("Recommendations for management")
st.markdown(
    theme.caption(
        "Ordered by how well the evidence supports acting, not by how "
        "appealing the action is."
    ),
    unsafe_allow_html=True,
)
st.write("")

m1, m2 = st.columns(2, gap="medium")

with m1:
    st.markdown(
        card(
            "Protect mature forest where Wood Thrush is present",
            f"The at-risk signal is real and repeats in every shared park, but "
            f"it is <b>one species</b> carrying {q1b['wood_thrush_share_pct']}% "
            f"of it. Framing this as a Wood Thrush measure rather than a "
            f"general at-risk measure is both more accurate and easier to "
            f"defend if challenged.",
            "Act - high confidence", theme.FOREST,
            "Q1 and Q1b &middot; Report &sect;4.1",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Reduce disturbance during survey windows",
            f"A {dt['loss_pct']}% loss in recorded species is the largest "
            f"effect in the project. Disturbance is also the only "
            f"environmental variable that is a property of the site and the "
            f"schedule rather than the weather - which makes it the only one "
            f"anybody can actually change. The distribution matters as much as "
            f"the mean: serious disturbance shifts the whole distribution "
            f"down, not just its tail.",
            "Act - high confidence", theme.FOREST,
            "Q9 &middot; Report &sect;4.10 &middot; Environment page box plots",
        ),
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        card(
            "Do not convert grassland on diversity grounds",
            f"Grassland holds all {q4['n_grassland']} habitat specialists in "
            f"the dataset; forest holds none. Richness gives no reason to "
            f"prefer either habitat - and neither do Shannon, Simpson or "
            f"evenness, so this is not a matter of having measured diversity "
            f"the wrong way. A conversion argument built on \"more species\" "
            f"has no support here, and would remove the only habitat some of "
            f"these birds use.",
            "Do not act", theme.AT_RISK,
            "Q4 and Q13 &middot; Report &sect;4.5 and &sect;4.6",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Send at-risk monitoring and diversity visits to different parks",
            f"The park with the highest at-risk detection rate ranks last of "
            f"{q12['n_parks']} for species per session. \"Best park\" depends "
            f"entirely on the question being asked, and a single "
            f"recommendation list would send both audiences to the wrong "
            f"place.",
            "Act - moderate confidence", theme.GRASSLAND,
            "Q3 &middot; Report &sect;4.7.2 &middot; Where page",
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. design
st.subheader("Recommendations for survey design")
st.markdown(
    theme.caption(
        "These are the changes that would let the next season answer questions "
        "this one cannot. Each is costed in sessions below."
    ),
    unsafe_allow_html=True,
)
st.write("")

d1, d2 = st.columns(2, gap="medium")

with d1:
    st.markdown(
        card(
            f"Add grassland plots to the {len(single)} forest-only parks",
            f"All {len(single)} single-habitat parks are forest-only, holding "
            f"<b>{unusable:,} sessions</b> that currently cannot contribute to "
            f"the central question. Pairing habitats within those parks would "
            f"take usable data from <b>{q12['usable_pct']}%</b> to "
            f"<b>100%</b> without adding a single park.",
            "Highest value change", theme.FOREST,
            "Q12 &middot; Report &sect;5.3",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Calibrate surveyors on song and call recognition",
            f"{q14['auditory_pct']}% of detections are auditory, and "
            f"{q14['auditory_gap']:.2f} of the {obs_gap:.2f}-species observer "
            f"gap sits on that channel against {q14['visual_gap']:.2f} on the "
            f"visual one - with the ranking reversing between the two. A short "
            f"pre-season call-identification session targets the actual "
            f"mechanism. Nothing in the earlier analysis justified this "
            f"recommendation; the channel breakdown is what makes it specific "
            f"rather than a vague plea for consistency.",
            "New - targets the mechanism", theme.FOREST,
            "Q14 &middot; Report &sect;5.2",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Keep the observer rota balanced - and write it into the protocol",
            f"The {q10['spread_pct']}% observer spread is harmless here purely "
            f"because assignment was balanced across habitats and parks. That "
            f"was the single most consequential methodological choice anyone "
            f"made in this survey, and it currently exists as practice rather "
            f"than as a documented rule.",
            "Protect what already works", theme.FOREST,
            "Q10 &middot; Report &sect;5.1",
        ),
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        card(
            "Decouple visit number from calendar date",
            f"Visit number and day-of-season correlate at <b>rho 0.89</b>, and "
            f"third visits happened in grassland only. Rotating visit order "
            f"across plots - some plots surveyed late-first - would let a "
            f"genuine seasonal question be asked. At present it cannot be, and "
            f"no amount of analysis fixes that after the fact.",
            "Unlocks a whole question", theme.GRASSLAND,
            "Q6 &middot; Report &sect;4.9 &middot; Timing page",
        ),
        unsafe_allow_html=True,
    )
    lowtext = ", ".join(
        f"<b>{NAME[i]}</b> needs {RELIABLE_FLOOR - int(r['total'])} more"
        for i, r in low.iterrows()
    )
    st.markdown(
        card(
            f"Lift the smallest parks over the {RELIABLE_FLOOR}-session floor",
            f"Only two parks fall below it, and barely: {lowtext}. That is "
            f"{floor_cost} extra sessions to make two more parks reportable - "
            f"the cheapest improvement available anywhere in this list. Worth "
            f"stating plainly, though: both are forest-only, so this makes "
            f"them <i>reportable</i> without making them <i>usable</i> for the "
            f"habitat question. A real gain, and a smaller one than the low "
            f"price suggests.",
            "Cheap and immediate", theme.GRASSLAND,
            "Q12 and guardrail G3 &middot; Report &sect;5.4",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Extend beyond three visits per plot",
            f"No plot was visited more than three times, which makes "
            f"plot-level ranking impossible. The plot leaderboard on the Where "
            f"page is the right tail of a noisy distribution rather than a "
            f"list of good places, and it is labelled as such. Plot-scale "
            f"recommendations need substantially more repeat sampling before "
            f"they mean anything.",
            "Needed for plot-scale work", theme.GRASSLAND,
            "Q3 &middot; Report &sect;4.7.1",
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. cost
st.subheader("What each change costs, in sessions")

COSTS = [
    ("Write the rota rule into the protocol", 0),
    ("Rotate visit order across plots", 0),
    ("Pre-season call calibration", 0),
    (f"Lift {len(low)} parks over the {RELIABLE_FLOOR}-session floor",
     floor_cost),
    (f"Pair habitats in the {len(single)} forest-only parks", pair_cost),
]

c1, c2 = st.columns([0.58, 0.42], gap="large")

with c1:
    names = [n for n, _ in COSTS][::-1]
    costs = [c for _, c in COSTS][::-1]
    fig = go.Figure(go.Bar(
        x=costs, y=names, orientation="h",
        marker_color=[theme.GRASSLAND if c else theme.FOREST for c in costs],
        text=[f"{c} sessions" if c else "no extra sessions" for c in costs],
        textposition="outside",
        hovertemplate="%{y}<br>%{x} extra sessions<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="extra survey sessions required",
        **theme.plotly_layout(height=330, showlegend=False),
    )
    fig.update_xaxes(range=[0, pair_cost * 1.5])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Three of the five design recommendations cost no extra field "
            f"time at all - they are changes to how existing effort is "
            f"scheduled and recorded. Only two need more sessions, and "
            f"together they come to {floor_cost + pair_cost}, or "
            f"{(floor_cost + pair_cost) / q12['total_sessions'] * 100:.0f}% on "
            f"top of the {q12['total_sessions']:,} sessions the season already "
            f"runs."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-left:4px solid {theme.FOREST};border-radius:12px;
            padding:20px 22px">
  <div style="font-size:0.7rem;font-weight:700;color:{theme.FOREST};
              text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">
      Return on the largest investment</div>
  <div style="font-size:2rem;font-weight:800;color:{theme.FOREST};
              line-height:1.1">{pair_return:.1f}&times;</div>
  <div style="font-size:0.85rem;color:{theme.INK2};line-height:1.7;
              margin-top:10px">
      Every grassland session added to a forest-only park brings
      <b>{pair_return:.1f} previously unusable forest sessions</b> back into
      the analysis. {pair_cost} new sessions - {pair_pct:.0f}% more field
      time - would unlock the {unusable:,} sessions that currently cannot
      address the question this survey exists to answer.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        theme.caption(
            f"The costing assumes {RELIABLE_FLOOR} grassland sessions per "
            f"park, which is the same reliability floor used everywhere else "
            f"in this dashboard rather than a number chosen to flatter the "
            f"recommendation. Fewer would leave the new plots below the floor "
            f"and unreportable; more would improve precision at "
            f"proportionally higher cost."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 7. future
st.subheader("The study this one could not be")

st.markdown(
    f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:22px 26px;font-size:0.95rem;
            color:{theme.INK};line-height:1.75">
  <p style="margin:0 0 12px">
    Three of the design changes above are not refinements - each one converts
    a question this dataset has to refuse into one it could answer.
  </p>
  <p style="margin:0 0 10px">
    <b>Paired habitats in every park</b> would turn a null result within
    {q2['n_parks']} parks into a properly powered test across
    {q12['n_parks']}. The current answer - that habitat does not drive
    richness - rests on {q2['within_shared']['n_forest']} forest sessions.
    That is enough to reject a strong claim, not enough to prove equivalence.
  </p>
  <p style="margin:0 0 10px">
    <b>Rotated visit order</b> would separate seasonal change from
    repeat-visit fatigue. Right now those two explanations fit the July dip
    equally well and nothing distinguishes them.
  </p>
  <p style="margin:0 0 10px">
    <b>More visits per plot</b> would make plot-level work possible at all.
    With a maximum of three visits, individual plots cannot be ranked, and the
    leaderboard on the Where page is the right tail of a noisy distribution
    rather than a list of good places.
  </p>
  <p style="margin:12px 0 0;padding-top:14px;
            border-top:1px solid {theme.BORDER};color:{theme.INK2};
            font-size:0.9rem">
    None of these require more parks, more staff or a longer season. The
    largest of them costs {pair_pct:.0f}% more field time; the other two cost
    nothing but a change to the schedule.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")
st.divider()

# ------------------------------------------------------------------ 8. closing
st.subheader("If you remember one thing")

st.markdown(
    f"""
<div style="background:linear-gradient(140deg,{theme.KPI_TOP},{theme.KPI_BOTTOM});
            border-radius:16px;padding:28px 32px;color:#ffffff">
  <div style="font-size:1.15rem;font-weight:700;line-height:1.6;
              margin-bottom:14px">
    The strongest result in this project is that the habitat difference it was
    built to measure is smaller than the difference between the people doing
    the measuring.
  </div>
  <div style="font-size:0.95rem;line-height:1.75;color:#cfe3d6">
    Habitat moved species-per-session by <b>{hab_gap:.2f}</b>. Which of three
    surveyors held the clipboard moved it by <b>{obs_gap:.2f}</b>. Disturbance
    moved it by <b>{dt['none_mean'] - dt['serious_mean']:.2f}</b>.<br/><br/>
    That is not a disappointing outcome - it is the reason the guardrails
    exist, and the reason this dashboard reports what it rejected as carefully
    as what it found. A pooled comparison, an unbalanced rota or an
    unquestioned leaderboard would each have produced a confident, publishable,
    wrong answer.<br/><br/>
    It is also not a dead end. Splitting those detections by how the bird was
    identified showed that {q14['auditory_pct']}% of them are made by ear and
    that the surveyor gap lives almost entirely on that channel - which turns
    the project's most alarming finding into a half-day of pre-season call
    training. And the habitat signal that <i>does</i> survive is about which
    species are present rather than how many: Wood Thrush in forest,
    {q4['n_grassland']} specialists in grassland, and the same species list
    weighted differently between the two. That is a more useful finding than
    the one the study set out to make.
  </div>
</div>
""",
    unsafe_allow_html=True,
)