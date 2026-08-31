"""
Timing - when birds were easiest to find, and the one timing question this
dataset can actually answer fairly.

Layout, top to bottom:
  1. title
  2. monthly patterns (Q6) - shown for completeness but flagged descriptive
     only: forest sessions are badly imbalanced across months
  3. the reason it stays descriptive - visit number and calendar date are
     almost the same variable here (rho .89), so a "seasonal" decline cannot
     be separated from a repeat-visit decline. Q6's caveat, demonstrated.
  4. time-of-day (Q7) - the timing finding that does hold up: grassland
     species counts drop across the morning, checked two independent ways
  5. the same effect hour by hour, plus a check that it is about how many
     species turn up rather than which ones
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import stats_helpers as sh
import theme

res = da.results()
q6, q7 = res["q6"], res["q7"]
sessions = da.sessions()

BAND_ORDER = ["Early (5-6am)", "Mid (7-8am)", "Late (9-10am)"]

# ------------------------------------------------------------------ 1. title
st.title("Timing")
st.markdown(
    theme.caption(
        "Two timing questions, one answerable and one not. Like the other "
        "analysis pages these read from the guarded pipeline, so they don't "
        "follow the sidebar filters."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. monthly
st.subheader("Monthly patterns - descriptive only, not a trend")

c1, c2 = st.columns([0.6, 0.4], gap="large")

with c1:
    months = q6["table"].index.tolist()
    sp6 = q6["table"]["species_per_session"]
    eff = q6["effort"]

    fig = go.Figure()
    fig.add_bar(
        name="Forest", x=months, y=sp6["Forest"], marker_color=theme.FOREST,
        text=sp6["Forest"], textposition="outside",
    )
    fig.add_bar(
        name="Grassland", x=months, y=sp6["Grassland"], marker_color=theme.GRASSLAND,
        text=sp6["Grassland"], textposition="outside",
    )
    fig.update_layout(
        barmode="group", yaxis_title="species per session",
        **theme.plotly_layout(height=230),
    )
    fig.update_yaxes(range=[0, sp6.values.max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

    fig2 = go.Figure()
    fig2.add_bar(
        name="Forest", x=months, y=eff["Forest"], marker_color=theme.FOREST,
        showlegend=False, text=eff["Forest"], textposition="outside",
    )
    fig2.add_bar(
        name="Grassland", x=months, y=eff["Grassland"], marker_color=theme.GRASSLAND,
        showlegend=False, text=eff["Grassland"], textposition="outside",
    )
    fig2.update_layout(
        barmode="group", yaxis_title="sessions run",
        **theme.plotly_layout(height=200, showlegend=False),
    )
    fig2.update_yaxes(range=[0, eff.values.max() * 1.3])
    st.plotly_chart(fig2, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Bottom chart is the first problem: forest ran "
            f"{int(eff['Forest'].max())} sessions in June against only "
            f"{int(eff['Forest'].min())} in July - a "
            f"{q6['effort_imbalance']['Forest']}x gap - while grassland "
            f"stayed nearly flat ({q6['effort_imbalance']['Grassland']}x). "
            f"The second problem is below."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        theme.guardrail_banner(
            f"<b>Descriptive only.</b> {q6['caveat']} Read this section as "
            f"\"here is what the raw numbers look like\", not as a finding - "
            f"unlike the time-of-day result further down, nothing here was "
            f"tested for significance, and the next section shows why testing "
            f"it would not have helped."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. confound
st.subheader("Why \"seasonal decline\" isn't a claim this data can make")

visits = (
    sessions.groupby("Visit")
    .agg(sessions_run=("session_id", "size"),
         species_per_session=("species_per_session", "mean"),
         mean_day=("day_of_season", "mean"))
    .round(2)
    .reset_index()
)

rho_cal, p_cal = sh.spearmanr(
    sessions["Visit"].values, sessions["day_of_season"].values
)
rho_rich, p_rich = sh.spearmanr(
    sessions["Visit"].values, sessions["species_per_session"].values
)
rho_cal, rho_rich = round(rho_cal, 3), round(rho_rich, 3)


def _p(value: float) -> str:
    """A p-value small enough to underflow to 0.0 should not be printed as
    "p = 0", which reads like a bug rather than a very strong result."""
    return "p &lt; 1e-300" if value == 0 else f"p = {value:.3g}"


# Which habitats ever received a 3rd visit - forest never did, and that alone
# makes the late-season numbers a different mix of parks and habitats.
visit_hab = (
    sessions.groupby(["Visit", "habitat"]).size().unstack(fill_value=0)
)

c3, c4 = st.columns([0.55, 0.45], gap="large")

with c3:
    fig = go.Figure()
    fig.add_bar(
        x=visits["Visit"].astype(str), y=visits["species_per_session"],
        marker_color=theme.SEQUENTIAL[3], name="species per session",
        text=visits["species_per_session"], textposition="outside",
        customdata=visits[["sessions_run", "mean_day"]],
        hovertemplate="Visit %{x}<br>%{y} species / session<br>"
                      "%{customdata[0]} sessions<br>"
                      "average day %{customdata[1]} of the season"
                      "<extra></extra>",
    )
    fig.add_trace(go.Scatter(
        x=visits["Visit"].astype(str), y=visits["mean_day"],
        mode="lines+markers", name="average day of season",
        yaxis="y2", line={"color": theme.AT_RISK, "width": 2.4},
        marker={"size": 9, "color": theme.AT_RISK},
    ))
    # This chart overlays a second y-axis by hand rather than via
    # make_subplots, so the left-axis range has to be set inside the layout
    # dict - update_yaxes() would demand a subplot grid that doesn't exist.
    layout = theme.plotly_layout(height=340)
    layout["yaxis"]["title"] = "species per session"
    layout["yaxis"]["range"] = [0, visits["species_per_session"].max() * 1.35]
    fig.update_layout(
        xaxis_title="visit number",
        yaxis2={"title": "average day of season", "overlaying": "y",
                "side": "right", "showgrid": False,
                "title_font": {"size": 11, "color": theme.AT_RISK},
                "tickfont": {"size": 11, "color": theme.AT_RISK}},
        **layout,
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "The green bars fall and the red line climbs. Later visits are "
            "later in the season by construction - which is precisely why "
            "the two effects cannot be told apart."
        ),
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        theme.guardrail_banner(
            f"<b>Visit number and calendar date are nearly the same variable.</b> "
            f"They correlate at rho = {rho_cal} ({_p(p_cal)}). Richness "
            f"also falls with visit number (rho = {rho_rich}, "
            f"{_p(p_rich)}). So the July dip in the charts above is "
            f"equally consistent with \"birds get harder to find later in "
            f"summer\" and with \"observers record fewer species on a plot "
            f"they have already walked twice\" - and nothing in this dataset "
            f"separates the two."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:18px 20px">
  <div style="font-size:0.9rem;color:{theme.INK2};line-height:1.7">
      There is a second problem stacked on the first: the third visit happened
      in <b>grassland only</b> ({int(visit_hab.loc[3, 'Grassland'])} sessions,
      against {int(visit_hab.loc[3, 'Forest'])} in forest). Late-season
      numbers are therefore a different habitat mix as well as a different
      time - three confounds tangled into one axis.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. time of day
st.subheader("Early birds really do get more species - in grassland")

c5, c6 = st.columns([0.55, 0.45], gap="large")

with c5:
    bands = q7["table"].index.tolist()
    sp7 = q7["table"]["species_per_session"]
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_trace(go.Scatter(
            x=bands, y=sp7[hab], mode="lines+markers", name=hab,
            line={"color": colour, "width": 2.4},
            marker={"size": 9, "color": colour},
        ))
    fig.update_layout(
        yaxis_title="species per session",
        **theme.plotly_layout(height=340),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Unlike the months above, sessions are spread across all three "
            "bands in both habitats, nothing is entangled with visit number, "
            "and the pattern was checked two independent ways."
        ),
        unsafe_allow_html=True,
    )

with c6:
    g = q7["early_vs_late"]["Grassland"]
    f = q7["early_vs_late"]["Forest"]
    gt = q7["trend"]["Grassland"]
    ft = q7["trend"]["Forest"]
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">
      Grassland</div>
  <div style="font-size:1.5rem;font-weight:800;color:{theme.GRASSLAND}">
      {g['early_mean']} <span style="font-size:1rem;color:{theme.MUTED}">early</span>
      &nbsp;→&nbsp;
      {g['late_mean']} <span style="font-size:1rem;color:{theme.MUTED}">late</span>
  </div>
  <div style="font-size:0.88rem;color:{theme.INK2};margin-top:6px;line-height:1.6">
      {g['gain_pct']}% more species early, p = {g['p_value']:.1e} →
      <b style="color:{theme.FOREST}">significant</b>.<br/>
      Whole-morning trend agrees: rho = {gt['rho']}, p = {gt['p_value']:.1e}.
  </div>
  <div style="height:1px;background:{theme.BORDER};margin:16px 0"></div>
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">
      Forest</div>
  <div style="font-size:1.5rem;font-weight:800;color:{theme.FOREST}">
      {f['early_mean']} <span style="font-size:1rem;color:{theme.MUTED}">early</span>
      &nbsp;→&nbsp;
      {f['late_mean']} <span style="font-size:1rem;color:{theme.MUTED}">late</span>
  </div>
  <div style="font-size:0.88rem;color:{theme.INK2};margin-top:6px;line-height:1.6">
      {f['gain_pct']}% more species early, p = {f['p_value']:.2f} →
      <b style="color:{theme.MUTED}">not significant</b>.<br/>
      Whole-morning trend agrees: rho = {ft['rho']}, p = {ft['p_value']:.2f}.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.write("")

# ---- 4b. the same three bands as distributions --------------------------
d1, d2 = st.columns([0.55, 0.45], gap="large")

with d1:
    st.markdown("**The same three bands, as distributions**")
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        sub = sessions[sessions.habitat == hab]
        for band in BAND_ORDER:
            vals = sub.loc[sub.time_band == band, "species_per_session"]
            fig.add_trace(go.Box(
                y=vals, x=[band] * len(vals), name=hab, legendgroup=hab,
                showlegend=(band == BAND_ORDER[0]),
                boxmean=True, marker_color=colour,
                hovertemplate="%{y} species<extra></extra>",
            ))
    fig.update_layout(
        boxmode="group",
        yaxis_title="species per session",
        xaxis_title="time band",
        **theme.plotly_layout(height=380),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

with d2:
    gm = [
        sessions.loc[(sessions.habitat == "Grassland")
                     & (sessions.time_band == b), "species_per_session"].median()
        for b in BAND_ORDER
    ]
    fm = [
        sessions.loc[(sessions.habitat == "Forest")
                     & (sessions.time_band == b), "species_per_session"].median()
        for b in BAND_ORDER
    ]
    st.markdown(
        theme.guardrail_banner(
            f"<b>The medians move too, which the means alone would not tell "
            f"you.</b> Grassland steps down at every band - "
            f"{gm[0]:.0f} → {gm[1]:.0f} → {gm[2]:.0f} species - so the "
            f"whole distribution slides, not just a handful of unusually rich "
            f"early sessions. Forest sits at "
            f"{fm[0]:.0f} → {fm[1]:.0f} → {fm[2]:.0f} and if anything "
            f"ends the morning slightly higher, which is what a genuinely flat "
            f"result looks like."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            "Boxes are quartiles, the solid line the median and the dashed "
            "line the mean. The two habitats overlap heavily at every band - "
            "the grassland effect is a shift in a wide distribution, not a "
            "separation between two clean groups."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. detail
st.subheader("The same effect hour by hour, and what it is not")

hourly = (
    sessions.groupby(["start_hour", "habitat"])
    .species_per_session.agg(["size", "mean"])
    .round(2).unstack()
)
at_risk = (
    sessions.groupby(["time_band", "habitat"])
    .has_at_risk.mean().mul(100).round(1).unstack()
    .reindex(BAND_ORDER)
)
duration = sessions.groupby("time_band").session_duration_min.mean().round(1)

c7, c8 = st.columns(2, gap="large")

with c7:
    st.markdown("**Species per session, by exact start hour**")
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_trace(go.Scatter(
            x=[f"{h}am" for h in hourly.index],
            y=hourly["mean"][hab], mode="lines+markers", name=hab,
            line={"color": colour, "width": 2.4},
            marker={"size": 9, "color": colour},
            customdata=hourly["size"][hab],
            hovertemplate="%{x}<br>%{y} species / session<br>"
                          "%{customdata} sessions<extra></extra>",
        ))
    fig.update_layout(
        xaxis_title="session start hour",
        yaxis_title="species per session",
        **theme.plotly_layout(height=320),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Grassland peaks at 6am and slides from there; forest stays "
            f"within half a species all morning. Sessions last "
            f"{duration.min()}-{duration.max()} minutes regardless of band, "
            f"so this is not a case of early surveys simply running longer."
        ),
        unsafe_allow_html=True,
    )

with c8:
    st.markdown("**At-risk detection, by time band**")
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        fig.add_bar(
            name=hab, x=BAND_ORDER, y=at_risk[hab], marker_color=colour,
            text=at_risk[hab].map(lambda v: f"{v}%"), textposition="outside",
        )
    fig.update_layout(
        barmode="group",
        yaxis_title="% of sessions recording an at-risk species",
        **theme.plotly_layout(height=320),
    )
    fig.update_yaxes(range=[0, at_risk.values.max() * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Flat in forest, and low and unsteady in grassland - no morning "
            "advantage in either. Whatever the early hours give you, it is "
            "not a better chance of finding a declining species."
        ),
        unsafe_allow_html=True,
    )

st.markdown(
    theme.guardrail_banner(
        "<b>What this page supports saying.</b> Survey grassland plots early "
        "if the goal is the longest species list - that one is tested, "
        "replicated across two methods, and free of the confounds that sink "
        "the monthly view. It does not support scheduling around at-risk "
        "species, timing forest surveys at all, or any statement about the "
        "season. Three of the four timing questions this dataset invites are "
        "questions it cannot answer, and saying so is part of the result."
    ),
    unsafe_allow_html=True,
)