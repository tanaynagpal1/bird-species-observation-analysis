"""
Environment - weather, sky, wind and disturbance, and a closing look at how
big any of it actually is.

Layout, top to bottom:
  1. title
  2. disturbance (Q9) - the strongest environmental effect in the dataset,
     with an anomaly we did not smooth away, plus the same breakdown run
     separately in each habitat to show the anomaly replicates
  3. where disturbance happens - the one part of this page a manager can act
     on, since disturbance is a property of the site, not the weather
  4. temperature (Q8) - the correlation coefficient says "colder is better",
     the curve says otherwise. A monotonic statistic describing a hump-shaped
     relationship is the trap on this page.
  5. humidity, sky and wind - smaller effects, and one more appearance of
     guardrail G3
  6. everything in scale - every effect on the dashboard in the same units,
     including the habitat difference the study was designed to measure
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q2, q7, q8, q9, q10 = res["q2"], res["q7"], res["q8"], res["q9"], res["q10"]
sessions = da.sessions()
coords = da.park_coordinates()

RELIABLE_FLOOR = 30

# Severity order, not value order - the whole point of the first chart is that
# the bars do NOT descend cleanly, and sorting by value would hide that.
DIST_ORDER = [
    "No effect on count",
    "Slight effect on count",
    "Moderate effect on count",
    "Serious effect on count",
]
DIST_SHORT = ["None", "Slight", "Moderate", "Serious"]
DIST_COLOURS = [theme.FOREST, theme.FOREST, theme.GRASSLAND, theme.AT_RISK]

WIND_ORDER = [
    "Calm (< 1 mph) smoke rises vertically",
    "Light air movement (1-3 mph) smoke drifts",
    "Light breeze (4-7 mph) wind felt on face",
    "Gentle breeze (8-12 mph), leaves in motion",
]
WIND_SHORT = ["Calm", "Light air", "Light breeze", "Gentle breeze"]

SKY_ORDER = [
    "Clear or Few Clouds", "Partly Cloudy", "Cloudy/Overcast",
    "Fog", "Mist/Drizzle",
]
SKY_SHORT = ["Clear", "Partly cloudy", "Overcast", "Fog", "Mist/drizzle"]

# ------------------------------------------------------------------ 1. title
st.title("Environment")
st.markdown(
    theme.caption(
        "Weather, conditions and disturbance - what moves the numbers, what "
        "misleads, and how any of it compares to the habitat difference this "
        "study set out to measure."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. disturbance
st.subheader("Disturbance is the strongest effect in the dataset")

c1, c2 = st.columns([0.55, 0.45], gap="large")

dist = q9["disturbance"].reindex(
    [d for d in DIST_ORDER if d in q9["disturbance"].index]
)
dt = q9["disturbance_test"]

with c1:
    fig = go.Figure(go.Bar(
        x=DIST_SHORT[:len(dist)],
        y=dist["species_per_session"],
        marker_color=DIST_COLOURS[:len(dist)],
        text=dist["species_per_session"],
        textposition="outside",
        customdata=dist["sessions_run"],
        hovertemplate="%{x}<br>%{y} species / session<br>"
                      "%{customdata} sessions<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="disturbance recorded during the session",
        yaxis_title="species per session",
        **theme.plotly_layout(height=330, showlegend=False),
    )
    fig.update_yaxes(range=[0, dist["species_per_session"].max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Session counts behind each bar: "
            + ", ".join(
                f"{short} {int(n)}"
                for short, n in zip(DIST_SHORT, dist["sessions_run"])
            )
            + f". All four clear the {RELIABLE_FLOOR}-session floor, so none "
              f"of these bars is a small-sample artefact."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:2.4rem;font-weight:800;color:{theme.AT_RISK};line-height:1">
      -{dt['loss_pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      fewer species when disturbance seriously affected the count
  </div>
  <div style="font-size:0.95rem;color:{theme.INK};line-height:1.7">
      <b>{dt['none_mean']}</b> species per session with no disturbance
      (n = {dt['n_none']}) against <b>{dt['serious_mean']}</b> when it
      seriously affected the count (n = {dt['n_serious']}).<br/>
      p = {dt['p_value']:.1e} &nbsp;→&nbsp;
      <b style="color:{theme.AT_RISK}">clearly significant</b>
  </div>
  <div style="margin-top:14px;font-size:0.88rem;color:{theme.INK2};line-height:1.6">
      A gap of <b>{dt['none_mean'] - dt['serious_mean']:.2f}</b> species per
      session - larger than any other effect measured in this project, and the
      only one that is about survey conditions rather than about the birds.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# The anomaly is easier to defend once you can see it happen twice.
dist_hab = (
    sessions.groupby(["Disturbance", "habitat"])
    .species_per_session.mean().round(2).unstack()
    .reindex([d for d in DIST_ORDER if d in q9["disturbance"].index])
)

c3, c4 = st.columns([0.45, 0.55], gap="large")

with c3:
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, x=DIST_SHORT[:len(dist_hab)], y=dist_hab[hab],
            marker_color=colour, text=dist_hab[hab], textposition="outside",
        )
    fig.update_layout(
        barmode="group", yaxis_title="species per session",
        **theme.plotly_layout(height=300),
    )
    fig.update_yaxes(range=[0, dist_hab.values.max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with c4:
    if q9["slight_exceeds_none_anomaly"]:
        st.markdown(
            theme.guardrail_banner(
                f"<b>An anomaly we left in.</b> \"Slight effect\" scores "
                f"<b>{dist.loc['Slight effect on count', 'species_per_session']}</b> "
                f"against \"no effect\" at "
                f"<b>{dist.loc['No effect on count', 'species_per_session']}</b> - "
                f"the bars go up before they go down, on "
                f"{int(dist.loc['Slight effect on count', 'sessions_run'])} and "
                f"{int(dist.loc['No effect on count', 'sessions_run'])} "
                f"sessions. Splitting by habitat shows it is not a fluke of one "
                f"subset: forest goes "
                f"{dist_hab.loc['No effect on count', 'Forest']} → "
                f"{dist_hab.loc['Slight effect on count', 'Forest']} and "
                f"grassland {dist_hab.loc['No effect on count', 'Grassland']} → "
                f"{dist_hab.loc['Slight effect on count', 'Grassland']}. It "
                f"replicates independently in both. We do not know why, and "
                f"inventing a mechanism would be worse than reporting it as "
                f"observed - the serious-vs-none result is unaffected either way."
            ),
            unsafe_allow_html=True,
        )

st.write("")

b1, b2 = st.columns([0.58, 0.42], gap="large")

with b1:
    st.markdown("**The same four groups, as distributions**")
    fig = go.Figure()
    for short, full, colour in zip(DIST_SHORT, DIST_ORDER, DIST_COLOURS):
        if full not in sessions["Disturbance"].unique():
            continue
        fig.add_trace(go.Box(
            y=sessions.loc[sessions["Disturbance"] == full,
                           "species_per_session"],
            name=short, marker_color=colour, boxmean=True,
            hovertemplate="%{y} species<extra></extra>",
        ))
    fig.update_layout(
        yaxis_title="species per session",
        xaxis_title="disturbance recorded during the session",
        **theme.plotly_layout(height=330, showlegend=False),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with b2:
    med_none = sessions.loc[sessions["Disturbance"] == "No effect on count",
                            "species_per_session"].median()
    med_slight = sessions.loc[sessions["Disturbance"] == "Slight effect on count",
                              "species_per_session"].median()
    med_serious = sessions.loc[sessions["Disturbance"] == "Serious effect on count",
                               "species_per_session"].median()
    st.markdown(
        theme.guardrail_banner(
            f"<b>The anomaly is in the tail, not the middle.</b> \"None\" and "
            f"\"slight\" have <b>identical medians</b> "
            f"({med_none:.0f} and {med_slight:.0f}) even though their means "
            f"differ ({dist.loc['No effect on count', 'species_per_session']} "
            f"against "
            f"{dist.loc['Slight effect on count', 'species_per_session']}). "
            f"So slight disturbance is not lifting the typical session - it is "
            f"associated with a heavier upper tail. Any explanation has to "
            f"account for that specific shape, which is a much narrower "
            f"requirement than \"why is slight better\"."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            f"Serious disturbance, by contrast, shifts the whole distribution: "
            f"its median drops to {med_serious:.0f}. That is what a real "
            f"effect looks like next to an artefact of the tail."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. where
st.subheader("Where disturbance happens")

bad = sessions.copy()
bad["disrupted"] = bad["Disturbance"].isin(
    ["Moderate effect on count", "Serious effect on count"]
)
by_park = (
    bad.groupby("Admin_Unit_Code")
    .agg(sessions_run=("session_id", "size"), disrupted=("disrupted", "mean"))
)
by_park["pct"] = (by_park["disrupted"] * 100).round(1)
by_park["reliable"] = by_park["sessions_run"] >= RELIABLE_FLOOR
by_park = by_park.merge(
    coords[["Admin_Unit_Code", "park_name"]].set_index("Admin_Unit_Code"),
    left_index=True, right_index=True,
).sort_values("pct")

c5, c6 = st.columns([0.58, 0.42], gap="large")

with c5:
    fig = go.Figure(go.Bar(
        y=by_park["park_name"], x=by_park["pct"], orientation="h",
        marker_color=[
            theme.AT_RISK if ok else theme.MUTED for ok in by_park["reliable"]
        ],
        text=by_park["pct"].map(lambda v: f"{v}%"), textposition="outside",
        customdata=by_park[["sessions_run"]],
        hovertemplate="<b>%{y}</b><br>%{x}% of sessions disrupted<br>"
                      "%{customdata[0]} sessions<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="% of sessions with moderate or serious disturbance",
        **theme.plotly_layout(height=400, showlegend=False),
    )
    fig.update_xaxes(range=[0, by_park["pct"].max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Grey bars ran under {RELIABLE_FLOOR} sessions (guardrail G3) and "
            f"should be read as indicative only."
        ),
        unsafe_allow_html=True,
    )

with c6:
    worst = by_park[by_park["reliable"]].iloc[-1]
    best = by_park[by_park["reliable"]].iloc[0]
    st.markdown(
        theme.guardrail_banner(
            f"<b>This is the actionable half of the page.</b> Weather cannot be "
            f"scheduled around; disturbance largely can. "
            f"{worst['park_name']} recorded moderate or serious disturbance in "
            f"<b>{worst['pct']}%</b> of its sessions against "
            f"<b>{best['pct']}%</b> at {best['park_name']} - a difference in "
            f"survey conditions, not in bird life, and one that costs recorded "
            f"species wherever it is high."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            "The parks at the top of this list are linear and urban sites - "
            "parkways and city parks, where roads and footfall run alongside "
            "the plots. That is a plausible reading of the pattern rather than "
            "a tested claim; the percentages themselves are simply counts."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. temperature
st.subheader("Temperature: where the correlation coefficient lies")

c7, c8 = st.columns([0.55, 0.45], gap="large")

temp = q8["temperature"]
peak = q8["temperature_peak_band"]

with c7:
    colours = [
        theme.FOREST if band == peak else theme.SEQUENTIAL[2]
        for band in temp.index
    ]
    fig = go.Figure(go.Bar(
        x=temp.index, y=temp["species_per_session"],
        marker_color=colours,
        text=temp["species_per_session"], textposition="outside",
        customdata=temp["sessions_run"],
        hovertemplate="%{x}<br>%{y} species / session<br>"
                      "%{customdata} sessions<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="temperature band",
        yaxis_title="species per session",
        **theme.plotly_layout(height=330, showlegend=False),
    )
    fig.update_yaxes(range=[0, temp["species_per_session"].max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Richness peaks at {peak} and falls away on <i>both</i> sides. "
            f"The coldest band sits below the peak, not above it - so "
            f"\"colder is better\" is wrong at the cold end, which is exactly "
            f"where the correlation alongside points."
        ),
        unsafe_allow_html=True,
    )

with c8:
    ft = q8["correlations"]["Forest_Temperature"]
    gt = q8["correlations"]["Grassland_Temperature"]
    st.markdown(
        theme.guardrail_banner(
            f"<b>Read the curve, not the coefficient.</b> Spearman's rho is a "
            f"<i>monotonic</i> statistic - it assumes the relationship only "
            f"ever goes one way. Applied here it returns "
            f"{ft['rho']} for forest (p = {ft['p_value']:.1e}) and "
            f"{gt['rho']} for grassland (p = {gt['p_value']:.1e}): both "
            f"significant, both negative, both summarising a hump as if it "
            f"were a slope. The number isn't wrong, but read alone it would "
            f"tell you the coldest mornings are the best ones - and the chart "
            f"says they aren't."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:18px 20px;margin-top:2px">
  <div style="font-size:0.9rem;color:{theme.INK2};line-height:1.7">
      What the chart supports saying: the warm end genuinely is worse.
      Richness falls from <b>{temp.loc[peak, 'species_per_session']}</b> at
      the {peak} peak to
      <b>{temp['species_per_session'].iloc[-1]}</b> above 30C.<br/><br/>
      What it does not support: any claim about cold mornings being better
      than mild ones.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------- temp x humidity grid
st.subheader("Temperature and humidity together")

TEMP_ORDER = ["<15C", "15-20C", "20-25C", "25-30C", ">30C"]
HUM_ORDER = ["<40%", "40-60%", "60-80%", ">80%"]

grid_mean = sessions.pivot_table(
    index="temp_band", columns="humidity_band",
    values="species_per_session", aggfunc="mean").round(2)
grid_n = sessions.pivot_table(
    index="temp_band", columns="humidity_band",
    values="species_per_session", aggfunc="size")
rows_ = [t for t in TEMP_ORDER if t in grid_mean.index]
cols_ = [h for h in HUM_ORDER if h in grid_mean.columns]
grid_mean = grid_mean.reindex(index=rows_, columns=cols_)
grid_n = grid_n.reindex(index=rows_, columns=cols_)

# Blank out any cell below the reliability floor. Leaving them in would put
# the highest numbers on the chart on top of two- and three-session samples.
reliable_mask = grid_n.fillna(0) >= RELIABLE_FLOOR
shown = grid_mean.where(reliable_mask)

t1, t2 = st.columns([0.58, 0.42], gap="large")

with t1:
    text = [[
        (f"{shown.loc[r, c]:.1f}<br><span style='font-size:9px'>"
         f"n={int(grid_n.loc[r, c])}</span>")
        if reliable_mask.loc[r, c]
        else (f"<span style='font-size:9px;color:#8a968d'>n="
              f"{int(grid_n.loc[r, c]) if pd.notna(grid_n.loc[r, c]) else 0}"
              f"</span>")
        for c in cols_] for r in rows_]
    fig = go.Figure(go.Heatmap(
        z=shown.values, x=cols_, y=rows_,
        colorscale=theme.SEQUENTIAL, showscale=True,
        colorbar={"title": "species /<br>session"},
        text=text, texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False,
        hovertemplate="%{y} · %{x}<br>%{z} species / session<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="humidity", yaxis_title="temperature",
        **theme.plotly_layout(height=360, showlegend=False),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with t2:
    n_ok = int(reliable_mask.sum().sum())
    best_cell = grid_mean.stack().idxmax()
    best_val = grid_mean.stack().max()
    best_n = int(grid_n.loc[best_cell[0], best_cell[1]])
    st.markdown(
        theme.guardrail_banner(
            f"<b>Only {n_ok} of {grid_mean.size} cells are reportable.</b> "
            f"Blank cells fall below the {RELIABLE_FLOOR}-session floor and "
            f"carry their session count only. The single highest figure in "
            f"this grid is <b>{best_val}</b> species per session at "
            f"{best_cell[0]} and {best_cell[1]} - on <b>{best_n} sessions</b>. "
            f"Plotted without the floor it would be the brightest cell on the "
            f"chart and completely meaningless."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            "Reading the reliable cells only: the temperature gradient runs "
            "down the rows and humidity adds little across them, which is "
            "consistent with the correlations above - temperature carries a "
            "real signal, humidity is marginal. There is no sign of the two "
            "interacting, though with nine usable cells this grid could not "
            "detect a subtle interaction anyway."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. the rest
st.subheader("Humidity, sky and wind")
st.markdown(
    theme.caption(
        "All three charts show species per session; hover any bar for the "
        "number of sessions behind it. None of the three was significance-"
        "tested as a category comparison."
    ),
    unsafe_allow_html=True,
)
st.write("")

hum = q8["humidity"]
sky = q9["sky"].reindex([s for s in SKY_ORDER if s in q9["sky"].index])
wind = q9["wind"].reindex([w for w in WIND_ORDER if w in q9["wind"].index])

c9, c10, c11 = st.columns(3, gap="medium")

with c9:
    st.markdown("**Humidity**")
    colours = [
        theme.MUTED if not ok else theme.SEQUENTIAL[3] for ok in hum["reliable"]
    ]
    fig = go.Figure(go.Bar(
        x=hum.index, y=hum["species_per_session"], marker_color=colours,
        text=hum["species_per_session"], textposition="outside",
        customdata=hum["sessions_run"],
        hovertemplate="%{x}<br>%{y} species / session<br>"
                      "%{customdata} sessions<extra></extra>",
    ))
    fig.update_layout(**theme.plotly_layout(height=250, showlegend=False))
    fig.update_yaxes(range=[0, hum["species_per_session"].max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with c10:
    st.markdown("**Sky**")
    fig = go.Figure(go.Bar(
        x=SKY_SHORT[:len(sky)], y=sky["species_per_session"],
        marker_color=theme.SEQUENTIAL[3],
        text=sky["species_per_session"], textposition="outside",
        customdata=sky["sessions_run"],
        hovertemplate="%{x}<br>%{y} species / session<br>"
                      "%{customdata} sessions<extra></extra>",
    ))
    fig.update_layout(**theme.plotly_layout(height=250, showlegend=False))
    fig.update_yaxes(range=[0, sky["species_per_session"].max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with c11:
    st.markdown("**Wind**")
    fig = go.Figure(go.Bar(
        x=WIND_SHORT[:len(wind)], y=wind["species_per_session"],
        marker_color=theme.SEQUENTIAL[3],
        text=wind["species_per_session"], textposition="outside",
        customdata=wind["sessions_run"],
        hovertemplate="%{x}<br>%{y} species / session<br>"
                      "%{customdata} sessions<extra></extra>",
    ))
    fig.update_layout(**theme.plotly_layout(height=250, showlegend=False))
    fig.update_yaxes(range=[0, wind["species_per_session"].max() * 1.3])
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

unreliable_hum = hum[~hum["reliable"]]
if len(unreliable_hum):
    band = unreliable_hum.index[0]
    st.markdown(
        theme.guardrail_banner(
            f"<b>Guardrail G3, one more time.</b> The grey {band} humidity bar "
            f"is the highest single number anywhere on this dashboard - "
            f"{unreliable_hum['species_per_session'].iloc[0]} species per "
            f"session - and it rests on "
            f"{int(unreliable_hum['sessions_run'].iloc[0])} sessions. That is "
            f"why it is greyed out rather than celebrated. Every other bar in "
            f"this row clears the {RELIABLE_FLOOR}-session floor."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. scale
st.subheader("Everything on this dashboard, in the same units")

t_rel = temp[temp["reliable"]]
sky_rel = q9["sky"][q9["sky"]["reliable"]]
wind_rel = q9["wind"][q9["wind"]["reliable"]]
hum_rel = hum[hum["reliable"]]
obs = q10["per_observer"]["species_per_session"]

# (label, gap in species per session, was it significance-tested and significant)
effects = [
    ("Disturbance (none → serious)",
     dt["none_mean"] - dt["serious_mean"], True),
    ("Observer (3 surveyors)", obs.max() - obs.min(), True),
    ("Sky (best → worst)",
     sky_rel["species_per_session"].max() - sky_rel["species_per_session"].min(),
     False),
    ("Temperature (best → worst band)",
     t_rel["species_per_session"].max() - t_rel["species_per_session"].min(),
     True),
    ("Time of day, grassland",
     q7["early_vs_late"]["Grassland"]["early_mean"]
     - q7["early_vs_late"]["Grassland"]["late_mean"], True),
    ("Wind (best → worst)",
     wind_rel["species_per_session"].max() - wind_rel["species_per_session"].min(),
     False),
    ("Humidity (best → worst)",
     hum_rel["species_per_session"].max() - hum_rel["species_per_session"].min(),
     False),
    ("Time of day, forest",
     q7["early_vs_late"]["Forest"]["early_mean"]
     - q7["early_vs_late"]["Forest"]["late_mean"], False),
    ("<b>Habitat (within shared parks)</b>",
     abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"]), False),
]
eff = pd.DataFrame(effects, columns=["label", "gap", "tested"])
eff = eff.sort_values("gap")

c12, c13 = st.columns([0.62, 0.38], gap="large")

with c12:
    fig = go.Figure()
    for tested, name, colour in [
        (True, "Tested, and significant", theme.FOREST),
        (False, "Not tested, or not significant", theme.MUTED),
    ]:
        sub = eff[eff["tested"] == tested]
        fig.add_bar(
            name=name, y=sub["label"], x=sub["gap"], orientation="h",
            marker_color=colour,
            text=sub["gap"].map(lambda v: f"{v:.2f}"), textposition="outside",
            hovertemplate="%{y}<br>%{x:.2f} species / session<extra></extra>",
        )
    fig.update_layout(
        barmode="stack",
        xaxis_title="gap in species per session, best category to worst",
        **theme.plotly_layout(height=420),
    )
    fig.update_xaxes(range=[0, eff["gap"].max() * 1.2])
    # Two traces give a real legend, but Plotly would otherwise group the bars
    # by trace and destroy the magnitude ordering - which is the entire point
    # of the chart. Pin the category order to the sorted labels instead.
    fig.update_yaxes(categoryorder="array", categoryarray=eff["label"].tolist())
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with c13:
    hab_gap = abs(q2["within_shared"]["forest"] - q2["within_shared"]["grassland"])
    dist_gap = dt["none_mean"] - dt["serious_mean"]
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:2.2rem;font-weight:800;color:{theme.AT_RISK};line-height:1">
      {dist_gap / hab_gap:.0f}×</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      disturbance matters more than habitat
  </div>
  <div style="font-size:0.92rem;color:{theme.INK};line-height:1.7">
      The habitat difference this survey was built to measure is
      <b>{hab_gap:.2f}</b> species per session - the smallest bar on the
      chart. Disturbance is <b>{dist_gap:.2f}</b>, and which of three people
      held the clipboard is <b>{obs.max() - obs.min():.2f}</b>.
  </div>
  <div style="margin-top:14px;font-size:0.88rem;color:{theme.INK2};line-height:1.65">
      That is not a failure of the study. It is the study's most useful
      result: on species richness, habitat is swamped by survey conditions
      and by the surveyor. The habitat signal that <i>does</i> survive is
      about <i>which</i> species are present - at-risk birds and grassland
      specialists - not how many.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown(
    theme.guardrail_banner(
        "<b>How to read this chart, and how not to.</b> Each bar is the range "
        "between the best and worst category of that variable, in species per "
        "session - a like-for-like comparison of magnitude, not a standardised "
        "effect size. Unreliable categories (under "
        f"{RELIABLE_FLOOR} sessions) are excluded before taking each range, so "
        "no bar rests on a 12-session outlier. Green bars were significance-"
        "tested and passed; grey bars were either never tested as a category "
        "comparison or were tested and failed. A wide grey bar means "
        "\"interesting, unverified\" - not \"strong effect\"."
    ),
    unsafe_allow_html=True,
)