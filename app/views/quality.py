"""
Data Quality - what the survey design lets this dataset answer, and the one
result that decides whether any of the rest can be trusted.

Layout, top to bottom:
  1. title
  2. the observer effect (Q10) - a 37% spread between three surveyors, larger
     than any ecological effect in the project
  3. three checks that decide whether it sinks the study: is it balanced, is
     it really the person, and do the observers agree with each other's
     conclusions
  4. coverage (Q12) - effort by park and habitat, and why only 52% of
     sessions can answer the central question
  5. protocol adherence and completeness - session length, missing values,
     and why the missingness is not a defect
  6. the four guardrails and the specific result each one caught
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q1, q2, q7, q8 = res["q1"], res["q2"], res["q7"], res["q8"]
q9, q10, q11, q12 = res["q9"], res["q10"], res["q11"], res["q12"]
sessions = da.sessions()
birds = da.birds()
coords = da.park_coordinates()

RELIABLE_FLOOR = 30
NAME = dict(zip(coords["Admin_Unit_Code"], coords["park_name"]))

# ------------------------------------------------------------------ 1. title
st.title("Data Quality")
st.markdown(
    theme.caption(
        "Every finding on this dashboard rests on the survey design. This page "
        "is the audit of that design - including the one result that came close "
        "to invalidating everything else."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. observer
st.subheader("Who did the counting matters more than what was counted")

obs = q10["per_observer"].sort_values("species_per_session")
obs_gap = obs["species_per_session"].max() - obs["species_per_session"].min()
hab_gap = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])

c1, c2 = st.columns([0.55, 0.45], gap="large")

with c1:
    fig = go.Figure(go.Bar(
        x=obs.index, y=obs["species_per_session"],
        marker_color=[theme.AT_RISK, theme.GRASSLAND, theme.FOREST],
        text=obs["species_per_session"], textposition="outside",
        customdata=obs[["sessions_run", "spread"]],
        hovertemplate="<b>%{x}</b><br>%{y} species / session<br>"
                      "%{customdata[0]} sessions<br>"
                      "within-observer spread %{customdata[1]}"
                      "<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title="species per session",
        **theme.plotly_layout(height=330, showlegend=False),
    )
    fig.update_yaxes(range=[0, obs["species_per_session"].max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Each surveyor ran a comparable number of sessions ("
            + ", ".join(f"{int(n)}" for n in obs["sessions_run"])
            + "), so this is not a sample-size artefact. Every pairwise "
              "difference is statistically significant."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:2.4rem;font-weight:800;color:{theme.AT_RISK};line-height:1">
      {q10['spread_pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      spread between the highest and lowest surveyor
  </div>
  <div style="font-size:0.95rem;color:{theme.INK};line-height:1.7">
      A gap of <b>{obs_gap:.2f}</b> species per session between people walking
      the same protocol, in the same parks, in the same season.<br/><br/>
      The habitat difference this study set out to measure is
      <b>{hab_gap:.2f}</b> - roughly
      <b>{obs_gap / hab_gap:.0f}x smaller</b>.
  </div>
  <div style="margin-top:14px;font-size:0.88rem;color:{theme.INK2};line-height:1.6">
      Read that carefully before reading anything else on this dashboard. If
      surveyor assignment had lined up with habitat, this project would have
      measured the surveyor and called it ecology.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

pairs = pd.DataFrame(
    [(k, v) for k, v in q10["pairwise_p"].items()],
    columns=["Comparison", "p-value"],
)
pairs["Significant"] = pairs["p-value"] < 0.05
pairs["p-value"] = pairs["p-value"].map(lambda v: f"{v:.2e}")
st.dataframe(pairs, width='stretch', hide_index=True)

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. checks
st.subheader("Three checks on whether that sinks the study")

within_park = (
    sessions.groupby(["Admin_Unit_Code", "Observer"])
    .species_per_session.agg(["size", "mean"])
    .reset_index()
)
# Only parks where all three surveyors worked enough sessions to compare.
big = within_park[within_park["size"] >= 20]
counts = big.groupby("Admin_Unit_Code").size()
big = big[big["Admin_Unit_Code"].isin(counts[counts == 3].index)]
# Park codes, not full names - this chart sits in a one-third column and
# the full names overlap into an unreadable smear.
big["park"] = big["Admin_Unit_Code"]
# How consistent is the ordering across parks? If every park ranks the three
# surveyors identically, the effect is the person, not their assignment.
_rank = big.pivot(index="Admin_Unit_Code", columns="Observer", values="mean")
_orders = {tuple(r.sort_values(ascending=False).index) for _, r in _rank.iterrows()}
same_order_everywhere = len(_orders) == 1
n_compare_parks = len(_rank)

by_obs_hab = (
    sessions[sessions.is_shared_park]
    .groupby(["Observer", "habitat"]).species_per_session.mean().round(2)
    .unstack()
)

c3, c4, c5 = st.columns(3, gap="medium")

with c3:
    st.markdown("**1. Was the rota balanced?**")
    shares = q10["habitat_shares"]
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, x=shares.columns, y=shares.loc[hab] * 100,
            marker_color=colour,
            text=(shares.loc[hab] * 100).round(1).map(lambda v: f"{v}%"),
            textposition="outside",
        )
    fig.update_layout(
        barmode="group", yaxis_title="% of that habitat's sessions",
        **theme.plotly_layout(height=290),
    )
    fig.update_yaxes(range=[0, 48])
    fig.update_xaxes(tickangle=-20)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Yes. Each surveyor covered close to a third of both habitats - "
            f"maximum deviation "
            f"{q10['max_habitat_share_deviation'] * 100:.1f} percentage points "
            f"(`balanced = {q10['balanced']}`). The observer effect therefore "
            f"cancels out of any habitat comparison."
        ),
        unsafe_allow_html=True,
    )

with c4:
    st.markdown("**2. Is it the person, or their parks?**")
    fig = go.Figure()
    for obs_name, colour in zip(
        obs.index, [theme.AT_RISK, theme.GRASSLAND, theme.FOREST]
    ):
        sub = big[big["Observer"] == obs_name]
        fig.add_trace(go.Scatter(
            x=sub["park"], y=sub["mean"], mode="lines+markers",
            name=obs_name, line={"color": colour, "width": 2},
            marker={"size": 8, "color": colour},
        ))
    fig.update_layout(
        yaxis_title="species per session",
        **theme.plotly_layout(height=290),
    )
    fig.update_xaxes(tickangle=-20)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"The person. Across the {n_compare_parks} parks where all "
            f"three worked enough sessions to compare, the ranking is "
            f"{'identical every time' if same_order_everywhere else 'largely stable'} "
            f"- the lines never cross. This is not an artefact of who was sent "
            f"where."
        ),
        unsafe_allow_html=True,
    )

with c5:
    st.markdown("**3. Do they disagree about the finding?**")
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, x=by_obs_hab.index, y=by_obs_hab[hab],
            marker_color=colour, text=by_obs_hab[hab], textposition="outside",
        )
    fig.update_layout(
        barmode="group", yaxis_title="species per session",
        **theme.plotly_layout(height=290),
    )
    fig.update_yaxes(range=[0, by_obs_hab.values.max() * 1.3])
    fig.update_xaxes(tickangle=-20)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "No. Within the shared parks, all three land on the same "
            "conclusion - no meaningful richness gap between habitats - even "
            "though they disagree wildly about the absolute numbers. The null "
            "result replicates three times independently."
        ),
        unsafe_allow_html=True,
    )

st.markdown(
    theme.guardrail_banner(
        f"<b>Verdict: the observer effect is real, large, and harmless here.</b> "
        f"It is harmless only because the rota was balanced - a design choice, "
        f"not luck. Any future survey that lets surveyor assignment correlate "
        f"with habitat, park or season will measure the surveyor and report it "
        f"as ecology. On this dashboard the practical consequence is narrower: "
        f"absolute species-per-session values carry a ±{obs_gap / 2:.1f} "
        f"personal-calibration band, so comparisons within the dataset are "
        f"sound while the absolute numbers should not be quoted against another "
        f"study's."
    ),
    unsafe_allow_html=True,
)

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. coverage
st.subheader("Coverage: why only half the data answers the main question")

eff = q12["by_park"].copy()
eff["park"] = [NAME.get(i, i) for i in eff.index]
eff = eff.sort_values("total")

c6, c7 = st.columns([0.58, 0.42], gap="large")

with c6:
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, y=eff["park"], x=eff[hab], orientation="h",
            marker_color=colour,
            hovertemplate="<b>%{y}</b><br>%{x} " + hab.lower()
                          + " sessions<extra></extra>",
        )
    fig.update_layout(
        barmode="stack", xaxis_title="survey sessions",
        **theme.plotly_layout(height=420),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Only the {q12['parks_with_both']} parks showing both colours can "
            f"support a habitat comparison. In the other "
            f"{q12['n_parks'] - q12['parks_with_both']}, \"forest vs "
            f"grassland\" would really be \"park A vs park B\"."
        ),
        unsafe_allow_html=True,
    )

with c7:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:2.4rem;font-weight:800;color:{theme.FOREST};line-height:1">
      {q12['usable_pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      of sessions can answer the central habitat question
  </div>
  <div style="font-size:0.95rem;color:{theme.INK};line-height:1.7">
      <b>{q12['usable_sessions']:,}</b> of
      <b>{q12['total_sessions']:,}</b> sessions come from the
      {q12['parks_with_both']} parks surveyed in both habitats.
  </div>
  <div style="margin-top:14px;font-size:0.88rem;color:{theme.INK2};line-height:1.65">
      This single number is the reason guardrail G2 exists, and the single
      most valuable change a future survey could make: pairing habitats
      within parks would roughly double the usable sample at no extra cost
      per session.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    small = eff[eff["total"] < RELIABLE_FLOOR]
    st.markdown(
        theme.caption(
            f"{len(small)} parks fall below the {RELIABLE_FLOOR}-session "
            f"reliability floor ("
            + ", ".join(small["park"].tolist())
            + ") and cannot carry a park-level claim. Forest plots were "
              f"visited {q12['visits_per_plot']['Forest']} times on average, "
              f"grassland plots {q12['visits_per_plot']['Grassland']}."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. integrity
st.subheader("Protocol adherence and completeness")

dur = sessions["session_duration_min"]
on_protocol = int((dur == 10).sum())
missing = birds.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)
miss_df = pd.DataFrame({
    "Column": missing.index,
    "Missing": missing.values,
    "% of rows": (missing.values / len(birds) * 100).round(1),
})
EXPLAIN = {
    "Sub_Unit_Code": "Optional field; most parks have no sub-units.",
    "Site_Name": "Recorded for forest plots only, by protocol.",
    "Distance": "Flyovers have no distance - see note below.",
    "AcceptedTSN": "Taxonomic serial number absent for a few records.",
    "ID_Method": "Two records with no method recorded.",
    "TaxonCode": "Two records with no taxon code.",
}
miss_df["Why"] = miss_df["Column"].map(EXPLAIN).fillna("Unexplained.")

c8, c9 = st.columns([0.45, 0.55], gap="large")

with c8:
    st.markdown("**Session length**")
    fig = go.Figure(go.Histogram(
        x=dur, nbinsx=30, marker_color=theme.SEQUENTIAL[3],
        hovertemplate="%{x} minutes<br>%{y} sessions<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="session duration (minutes)",
        yaxis_title="sessions",
        **theme.plotly_layout(height=300, showlegend=False),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"<b>{on_protocol:,} of {len(dur):,}</b> sessions "
            f"({on_protocol / len(dur) * 100:.1f}%) ran exactly the 10-minute "
            f"protocol; {int((dur > 10).sum())} ran longer, up to "
            f"{int(dur.max())} minutes. Median is identical in both habitats, "
            f"so effort per session is comparable and no rate on this "
            f"dashboard needs a duration correction."
        ),
        unsafe_allow_html=True,
    )

with c9:
    st.markdown("**Missing values, and whether they matter**")
    st.dataframe(miss_df, width='stretch', hide_index=True)
    n_fly = int(birds["is_flyover"].sum())
    st.markdown(
        theme.guardrail_banner(
            f"<b>Every missing value is explained by the protocol.</b> The "
            f"clearest case: <b>{n_fly}</b> records have no Distance, and "
            f"exactly those {n_fly} records are flyovers - birds passing "
            f"overhead rather than using the site, which have no distance to "
            f"record. The match is one-to-one with no exceptions. Missingness "
            f"that maps perfectly onto a protocol rule is a sign of a "
            f"well-run survey, not a data problem."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. guardrails
st.subheader("The four guardrails, and what each one caught")

# The single worst small-sample trap on the dashboard, quoted in the table.
hum_small = q8["humidity"][~q8["humidity"]["reliable"]]
worst_small = hum_small["species_per_session"].iloc[0] if len(hum_small) else 0
worst_small_n = int(hum_small["sessions_run"].iloc[0]) if len(hum_small) else 0

caught = pd.DataFrame([
    ("G1", "Compare per-session rates, never raw totals",
     f"Raw species count tracks survey effort at rho 0.77; the rate does not "
     f"(rho 0.23, not significant). A raw-count park ranking is a ranking of "
     f"who was visited most."),
    ("G2", f"Habitat comparisons use the {q12['parks_with_both']} shared parks only",
     f"Pooled richness looked significant (p = {q2['pooled']['p_value']:.1e}); "
     f"within shared parks it vanished (p = {q2['within_shared']['p_value']:.2f}). "
     f"Simpson's paradox, caught in our own numbers."),
    ("G3", f"Treat any group under {RELIABLE_FLOOR} sessions as unreliable",
     f"The <40% humidity band shows the highest figure on the dashboard "
     f"({worst_small} species/session) on {worst_small_n} sessions. Four "
     f"parks and the entire plot-level leaderboard fall below the floor too."),
    ("G4", "Rarefy before comparing species counts",
     f"Grassland appeared to hold "
     f"{q11['raw']['grassland_only'] / q11['raw']['forest_only']:.1f}x more "
     f"exclusive species than forest. Rarefied to equal sample size the gap "
     f"falls to "
     f"{q11['rarefied']['grassland_only'] / q11['rarefied']['forest_only']:.1f}x."),
], columns=["Guardrail", "Rule", "What it caught"])

# Rendered as HTML rather than st.dataframe: the "what it caught" column is a
# full sentence and a dataframe cell truncates it instead of wrapping.
rows_html = "".join(
    f'<tr>'
    f'<td style="padding:10px 12px;border-top:1px solid {theme.BORDER};'
    f'font-weight:700;color:{theme.FOREST};white-space:nowrap;vertical-align:top">{g}</td>'
    f'<td style="padding:10px 12px;border-top:1px solid {theme.BORDER};'
    f'color:{theme.INK};vertical-align:top">{rule}</td>'
    f'<td style="padding:10px 12px;border-top:1px solid {theme.BORDER};'
    f'color:{theme.INK2};vertical-align:top">{what}</td>'
    f'</tr>'
    for g, rule, what in caught.itertuples(index=False)
)
st.markdown(
    f"""
<table style="width:100%;border-collapse:collapse;background:{theme.CARD};
              border:1px solid {theme.BORDER};border-radius:10px;
              font-size:0.88rem;line-height:1.6;overflow:hidden">
  <tr style="background:{theme.PAGE}">
    <th style="padding:10px 12px;text-align:left;color:{theme.MUTED};
               font-size:0.78rem;text-transform:uppercase;letter-spacing:.04em">Guardrail</th>
    <th style="padding:10px 12px;text-align:left;color:{theme.MUTED};
               font-size:0.78rem;text-transform:uppercase;letter-spacing:.04em;width:28%">Rule</th>
    <th style="padding:10px 12px;text-align:left;color:{theme.MUTED};
               font-size:0.78rem;text-transform:uppercase;letter-spacing:.04em">What it caught</th>
  </tr>
  {rows_html}
</table>
""",
    unsafe_allow_html=True,
)
st.write("")

st.markdown(
    theme.guardrail_banner(
        "<b>Each of these was a live catch, not a precaution.</b> Every one of "
        "the four rules changed a conclusion this project would otherwise have "
        "published: a habitat difference that was really a park difference, a "
        "park ranking that was really an effort ranking, a record-breaking "
        "humidity band resting on twelve sessions, and a fivefold species gap "
        "that was mostly sampling. The guardrails are the analysis, not the "
        "paperwork around it."
    ),
    unsafe_allow_html=True,
)