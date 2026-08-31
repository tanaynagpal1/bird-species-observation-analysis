"""
Overview - the page that answers "what is this and what did we find?"

Layout, top to bottom:
  1. title + what the current filters are showing
  2. guardrail banner (why the numbers here are per-session, not raw counts)
  3. five KPIs - these DO follow the filters
  4. the headline finding - Wood Thrush - which does NOT follow the filters,
     because it is a verified result computed on the four shared parks
  5. survey effort by park, and the most-recorded species
  6. a short note on the four guardrails
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

f = st.session_state.get("filters", {})

birds = da.apply_filters(da.birds(), f)
sess = da.apply_filters(da.sessions(), f)
res = da.results()
q14 = res["q14"]

# ------------------------------------------------------------------ 1. title
st.title("Bird Species Observation Analysis")
st.markdown(
    theme.caption(
        "11 National Park Service units · 2018 breeding season · forest and "
        "grassland point-count surveys<br/><b>Showing:</b> "
        + da.filter_summary(f, f.get("n_parks_total", 11))
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. banner
st.markdown(
    theme.guardrail_banner(
        "<b>How to read every number on this dashboard.</b> Grassland was surveyed "
        "far more often than forest, so raw totals say more about how hard people "
        "looked than about the birds. Everything here is expressed <b>per survey "
        "session</b>, and habitat comparisons are restricted to the four parks "
        "where both habitats were actually surveyed."
    ),
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ 3. KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Observations", f"{len(birds):,}")
k2.metric("Survey sessions", f"{len(sess):,}")
k3.metric("Species recorded", f"{birds['Scientific_Name'].nunique():,}")
k4.metric("Parks", f"{birds['Admin_Unit_Code'].nunique()}")
k5.metric("At-risk sightings", f"{int(birds['is_at_risk'].sum()):,}")

st.write("")

# ------------------------------------------------------------------ 4. headline
q1, q1b = res["q1"], res["q1b"]

st.subheader("The headline belongs to a single bird")

left, right = st.columns([0.44, 0.56], gap="large")

with left:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:3.1rem;font-weight:800;color:{theme.AT_RISK};
              line-height:1">{q1b['wood_thrush_share_pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:12px">
      of all at-risk sightings are Wood Thrush
      ({q1b['wood_thrush_sightings']} of {q1b['total_at_risk_sightings']})</div>
  <div style="font-size:0.9rem;color:{theme.INK2};line-height:1.65">
      Forest sessions record at-risk birds at <b>{q1['forest_pct']}%</b> against
      <b>{q1['grassland_pct']}%</b> in grassland - a <b>{q1['ratio']}×</b> gap that
      is statistically solid and repeats in all {q1['n_parks']} shared parks.<br/><br/>
      Take Wood Thrush out and the gap falls to
      <b>{q1b['without_wood_thrush']['ratio']}×</b> and survives in only
      <b>{q1b['parks_agreeing_without']} of {q1['n_parks']}</b> parks.<br/><br/>
      So the correct finding is not "forest shelters at-risk birds". It is
      <b>"forest shelters Wood Thrush"</b>, and Wood Thrush is carrying the
      other seven species on its back.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with right:
    w, wo = q1b["with_wood_thrush"], q1b["without_wood_thrush"]
    fig = go.Figure()
    fig.add_bar(
        name="Forest",
        x=["All 8 at-risk species", "Excluding Wood Thrush"],
        y=[w["forest"], wo["forest"]],
        marker_color=theme.FOREST,
        text=[f"{w['forest']}%", f"{wo['forest']}%"],
        textposition="outside",
    )
    fig.add_bar(
        name="Grassland",
        x=["All 8 at-risk species", "Excluding Wood Thrush"],
        y=[w["grassland"], wo["grassland"]],
        marker_color=theme.GRASSLAND,
        text=[f"{w['grassland']}%", f"{wo['grassland']}%"],
        textposition="outside",
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="% of sightings that are at-risk",
        **theme.plotly_layout(height=340),
    )
    fig.update_yaxes(range=[0, w["forest"] * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Shared parks only, all months - this chart ignores the sidebar "
            f"filters on purpose, because it is a verified result "
            f"(Mann-Whitney p = {q1['p_value']:.1e}). Changing the park mix would "
            f"change the answer, which is exactly the mistake guardrail G2 exists "
            f"to prevent."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. context
c1, c2 = st.columns([0.55, 0.45], gap="large")

with c1:
    st.subheader("Where the survey effort went")
    effort = (
        da.sessions()
        .groupby(["park_name", "habitat"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["Forest", "Grassland"], fill_value=0)
    )
    effort = effort.loc[effort.sum(axis=1).sort_values(ascending=True).index]

    fig = go.Figure()
    for hab in ["Forest", "Grassland"]:
        fig.add_bar(
            name=hab,
            y=effort.index,
            x=effort[hab],
            orientation="h",
            marker_color=theme.HABITAT_COLOURS[hab],
        )
    fig.update_layout(
        barmode="stack",
        xaxis_title="survey sessions",
        **theme.plotly_layout(height=380),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Only {res['q12']['parks_with_both']} of {res['q12']['n_parks']} parks "
            f"were surveyed in both habitats - "
            f"{res['q12']['usable_sessions']:,} of {res['q12']['total_sessions']:,} "
            f"sessions ({res['q12']['usable_pct']}%). Everywhere else, "
            f"'forest vs grassland' would really be 'park A vs park B'."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.subheader("Most-recorded species")
    top = (
        birds.groupby(["Common_Name", "is_at_risk"])
        .size()
        .reset_index(name="sightings")
        .sort_values("sightings", ascending=False)
        .head(12)
        .sort_values("sightings")
    )
    fig = go.Figure(
        go.Bar(
            y=top["Common_Name"],
            x=top["sightings"],
            orientation="h",
            marker_color=[
                theme.AT_RISK if r else theme.FOREST for r in top["is_at_risk"]
            ],
            text=top["sightings"],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title="sightings", **theme.plotly_layout(height=380, showlegend=False)
    )
    fig.update_xaxes(range=[0, top["sightings"].max() * 1.18])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Raw sighting counts, so this chart follows the sidebar filters. Any "
            "PIF Watchlist species that reaches the top twelve is drawn in red - "
            "usually none do, which is itself the point."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. spread
st.subheader("Behind every average, a distribution")
st.markdown(
    theme.caption(
        "Bar charts of means hide how much sessions vary. These three views "
        "show the same data as spread rather than as a single number - which "
        "is what makes the size of the observer and disturbance effects "
        "believable."
    ),
    unsafe_allow_html=True,
)
st.write("")

s1, s2, s3 = st.columns(3, gap="medium")

with s1:
    st.markdown("**Species per session**")
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_trace(go.Violin(
            y=sess[sess.habitat == hab]["species_per_session"],
            name=hab, line_color=colour, fillcolor=colour, opacity=0.55,
            box_visible=True, meanline_visible=True, points=False,
            hovertemplate="%{y} species<extra></extra>",
        ))
    fig.update_layout(
        yaxis_title="species per session",
        **theme.plotly_layout(height=300, showlegend=False),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Both habitats span roughly {int(sess.species_per_session.min())} "
            f"to {int(sess.species_per_session.max())} species. The medians "
            f"sit almost on top of each other - the habitat question is "
            f"decided inside this overlap, not between two distinct groups."
        ),
        unsafe_allow_html=True,
    )

with s2:
    st.markdown("**How birds were detected**")
    ms = q14["method_share"]
    fig = go.Figure(go.Bar(
        x=ms.index, y=ms.values,
        marker_color=[theme.FOREST, theme.SEQUENTIAL[3], theme.MUTED][:len(ms)],
        text=[f"{v}%" for v in ms.values], textposition="outside",
        customdata=q14["method_counts"].reindex(ms.index).values,
        hovertemplate="%{x}<br>%{y}% of detections<br>"
                      "%{customdata:,} records<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title="% of all detections",
        **theme.plotly_layout(height=300, showlegend=False),
    )
    fig.update_yaxes(range=[0, ms.max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"<b>{q14['auditory_pct']}% of detections are by ear</b>, not by "
            f"eye. That single fact turns out to explain the biggest effect "
            f"in the project - see Data Quality."
        ),
        unsafe_allow_html=True,
    )

with s3:
    st.markdown("**When in the count birds appear**")
    cum = q14["interval_cumulative"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(cum.index), y=cum.values, mode="lines+markers",
        line={"color": theme.FOREST, "width": 2.6},
        marker={"size": 9, "color": theme.FOREST},
        fill="tozeroy", fillcolor="rgba(18,128,92,0.10)",
        hovertemplate="by %{x}<br>%{y}% of detections made<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title="cumulative % of detections",
        **theme.plotly_layout(height=300, showlegend=False),
    )
    fig.update_yaxes(range=[0, 105])
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Half of all detections happen in the first 2.5 minutes "
            f"({q14['first_interval_pct']}%), and the curve has clearly "
            f"flattened by minute 10. The protocol length is well chosen - a "
            f"curve still climbing at the end would mean species were being "
            f"missed."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 7. calendar
st.subheader("The season, as it was actually surveyed")

cal = (
    sess.assign(week_start=pd.to_datetime(sess["Date"]).dt.to_period("W")
                .dt.start_time.dt.date)
    .groupby(["week_start", "habitat"]).size().unstack(fill_value=0)
    .reindex(columns=["Forest", "Grassland"], fill_value=0)
    .sort_index()
)

h1, h2 = st.columns([0.62, 0.38], gap="large")

with h1:
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, x=[str(d) for d in cal.index], y=cal[hab],
            marker_color=colour,
            hovertemplate="week of %{x}<br>%{y} " + hab.lower()
                          + " sessions<extra></extra>",
        )
    fig.update_layout(
        barmode="stack",
        xaxis_title="week beginning",
        yaxis_title="sessions run",
        **theme.plotly_layout(height=330),
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Effort is not evenly spread through the season, and the two "
            "habitats do not rise and fall together. That unevenness is why "
            "the Timing page reports monthly figures as descriptive only."
        ),
        unsafe_allow_html=True,
    )

with h2:
    # Park codes, not full names: this heatmap sits in a narrow column and the
    # full names get clipped on the left axis.
    grid = (
        sess.groupby(["Admin_Unit_Code", "month_name"]).size()
        .unstack(fill_value=0)
        .reindex(columns=[m for m in ["May", "June", "July"]
                          if m in sess["month_name"].unique()], fill_value=0)
    )
    grid = grid.loc[grid.sum(axis=1).sort_values().index]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=list(grid.columns), y=list(grid.index),
        colorscale=theme.SEQUENTIAL, showscale=True,
        colorbar={"title": "sessions"},
        hovertemplate="%{y}<br>%{x}: %{z} sessions<extra></extra>",
    ))
    fig.update_yaxes(tickfont={"size": 11})
    fig.update_layout(**theme.plotly_layout(height=330, showlegend=False))
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "The same effort as a park-by-month grid, parks by their "
            "four-letter code. Pale cells are months a park was barely "
            "visited - the gaps are as informative as the dense blocks."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 8. method
with st.expander("The four rules this dashboard follows"):
    st.markdown(
        """
| | Rule | Why |
|---|---|---|
| **G1** | Compare **rates per session**, never raw counts | Grassland ran far more sessions; raw totals measure effort, not birds |
| **G2** | Habitat comparisons use the **4 shared parks only** | Pooling all 11 compares parks while pretending to compare habitats |
| **G3** | Any group with **fewer than 30 sessions** is marked unreliable | Small samples produce confident-looking nonsense |
| **G4** | Distinct-species counts are **rarefied** | A bigger sample finds more species even when diversity is identical |
"""
    )
    st.markdown(
        theme.caption(
            "These are enforced in <code>src/analysis.py</code>, not just written "
            "down - the code raises an error rather than silently returning a "
            "pooled figure."
        ),
        unsafe_allow_html=True,
    )