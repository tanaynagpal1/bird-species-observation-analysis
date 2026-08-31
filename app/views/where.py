"""
Where - park-level patterns, and three ways a "best place to see birds"
ranking can mislead.

Layout, top to bottom:
  1. title
  2. the map - all 11 parks, positioned by coordinates, sized by sessions
     run, coloured by species per session
  3. the proof: raw species count tracks effort (rho .77), the effort-adjusted
     rate does not (rho .23, not significant). This is guardrail G1 shown
     rather than asserted.
  4. "same parks, different podium" - the two rankings disagree, and this is
     the consequence of the scatter above
  5. at-risk presence by park - the park that ranks last for diversity ranks
     first for at-risk birds, so "best park" depends entirely on the question
  6. the individual-plot leaderboard plus the distribution it came from -
     the top plots are the right tail of a noisy spread, not a discovery
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import stats_helpers as sh
import theme

res = da.results()
q3 = res["q3"]
coords = da.park_coordinates()
sessions = da.sessions()
birds = da.birds()

RELIABLE_FLOOR = 30

# ------------------------------------------------------------------ 1. title
st.title("Where")
st.markdown(
    theme.caption(
        "Park-level patterns, and a second guardrail lesson: ranking places "
        "by a raw total rewards whoever was visited more, same as ranking "
        "habitats does."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. map
st.subheader("11 parks, sized by effort, coloured by richness")

map_df = q3["parks_by_rate"].reset_index().merge(coords, on="Admin_Unit_Code")

# A true geo map (px.scatter_geo / scatter_map) turned out to have the same
# problem the earlier tile-based map had: Plotly fetches its coastline/state
# outline data from cdn.plot.ly at draw time for *every* scope, including
# "usa" - so on a connection that blocks that host (school/corporate
# networks, some Streamlit Cloud egress rules) the chart would render
# completely blank. This plot draws longitude/latitude directly as x/y
# instead, with no basemap layer, so nothing is fetched over the network at
# all - it works identically offline or online.
lat_mid = (map_df["latitude"].min() + map_df["latitude"].max()) / 2
# 1 degree of longitude covers less ground than 1 degree of latitude the
# further you are from the equator - this keeps the layout proportional.
aspect_ratio = 1 / math.cos(math.radians(lat_mid))

fig = go.Figure(go.Scatter(
    x=map_df["longitude"],
    y=map_df["latitude"],
    mode="markers",
    marker={
        "size": map_df["sessions_run"],
        "sizemode": "area",
        "sizeref": 2 * map_df["sessions_run"].max() / (34 ** 2),
        "sizemin": 7,
        "color": map_df["species_per_session"],
        "colorscale": theme.SEQUENTIAL,
        "colorbar": {"title": "species /<br>session"},
        "line": {"width": 1, "color": "#ffffff"},
    },
    customdata=map_df[[
        "park_name", "sessions_run", "species_per_session",
        "distinct_species", "reliable",
    ]],
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "sessions run: %{customdata[1]}<br>"
        "species / session: %{customdata[2]}<br>"
        "distinct species: %{customdata[3]}<br>"
        "30+ sessions (reliable): %{customdata[4]}"
        "<extra></extra>"
    ),
))
fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, title="")
fig.update_yaxes(
    showgrid=False, zeroline=False, showticklabels=False, title="",
    scaleanchor="x", scaleratio=aspect_ratio,
)
fig.update_layout(
    height=420,
    margin={"l": 10, "r": 10, "t": 10, "b": 10},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=theme.GRID,
    font={"color": theme.INK2, "size": 12,
          "family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"},
    hoverlabel={"bgcolor": theme.CARD, "bordercolor": theme.BORDER,
                "font": {"color": theme.INK, "size": 12}},
)
# on_select turns the map into a drill-through control: clicking a point
# reruns the page with that park selected, and the profile below appears.
# selection_mode="points" keeps it to a single click rather than a lasso.
#
# Clearing needs the counter below. Plotly does not emit a deselect event for
# a click on empty space, and Streamlit will not let a chart's selection state
# be reassigned directly - so the Close button bumps a nonce that is part of
# the widget key, which remounts the chart with an empty selection.
if "map_nonce" not in st.session_state:
    st.session_state["map_nonce"] = 0

selection = st.plotly_chart(
    fig, width='stretch', config=theme.PLOTLY_CONFIG,
    key=f"park_map_{st.session_state['map_nonce']}",
    on_select="rerun", selection_mode="points",
)

picked_idx = None
try:
    pts = selection["selection"]["points"]
    if pts:
        picked_idx = pts[0]["point_index"]
except (KeyError, TypeError, IndexError):
    picked_idx = None

unreliable = map_df[~map_df["reliable"]]["park_name"].tolist()
st.markdown(
    theme.caption(
        f"Positioned by latitude/longitude, marker size is sessions run, "
        f"colour is species per session - hover a point for its name. "
        + (
            f"{', '.join(unreliable)} ran under {RELIABLE_FLOOR} sessions "
            f"(guardrail G3) - treat their colour as a rough guess, not a "
            f"result. "
            if unreliable else ""
        )
        + "Points are illustrative for CHOH, GWMP, NACE and ROCR, which are "
          "linear or scattered parks rather than a single compact site."
    ),
    unsafe_allow_html=True,
)

st.markdown(
    theme.caption(
        "<b>Click any point to open that park's profile below.</b>"
    ),
    unsafe_allow_html=True,
)

# ------------------------------------------------------------- park drill-down
if picked_idx is not None:
    park = map_df.iloc[picked_idx]
    code = park["Admin_Unit_Code"]
    p_sessions = sessions[sessions["Admin_Unit_Code"] == code]
    p_birds = birds[birds["Admin_Unit_Code"] == code]

    rank_rate = int(map_df["species_per_session"].rank(
        ascending=False, method="min").iloc[picked_idx])
    rank_raw = int(map_df["distinct_species"].rank(
        ascending=False, method="min").iloc[picked_idx])
    at_risk_pct = round(float(p_sessions["has_at_risk"].mean() * 100), 1)
    disturbed_pct = round(float(p_sessions["Disturbance"].isin(
        ["Moderate effect on count", "Serious effect on count"]).mean() * 100), 1)

    st.write("")
    head, close = st.columns([0.82, 0.18])
    with close:
        if st.button("Close profile", width='stretch',
                     key="close_park_profile"):
            st.session_state["map_nonce"] += 1
            st.rerun()
    st.markdown(
        f"""
<div style="background:linear-gradient(140deg,{theme.KPI_TOP},{theme.KPI_BOTTOM});
            border-radius:14px 14px 0 0;padding:18px 24px;color:#ffffff">
  <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;
              color:#a8c6b3">Park profile · {code}</div>
  <div style="font-size:1.5rem;font-weight:800;line-height:1.3;margin-top:2px">
      {park['park_name']}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    k = st.columns(5, gap="small")
    kpis = [
        ("Sessions", f"{int(park['sessions_run']):,}",
         "reliable" if park["reliable"] else f"below the {RELIABLE_FLOOR} floor"),
        ("Species / session", f"{park['species_per_session']}",
         f"rank #{rank_rate} of {len(map_df)}"),
        ("Distinct species", f"{int(park['distinct_species'])}",
         f"rank #{rank_raw} of {len(map_df)} raw"),
        ("At-risk sessions", f"{at_risk_pct}%", "recorded a watchlist species"),
        ("Disturbed sessions", f"{disturbed_pct}%", "moderate or serious"),
    ]
    for col, (label, value, note) in zip(k, kpis):
        with col:
            st.markdown(
                f'<div style="background:{theme.CARD};border:1px solid '
                f'{theme.BORDER};border-top:none;padding:12px 14px;height:100%">'
                f'<div style="font-size:0.7rem;color:{theme.MUTED};'
                f'text-transform:uppercase;letter-spacing:.05em">{label}</div>'
                f'<div style="font-size:1.35rem;font-weight:800;'
                f'color:{theme.INK};line-height:1.3">{value}</div>'
                f'<div style="font-size:0.74rem;color:{theme.MUTED}">{note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")
    p1, p2, p3 = st.columns(3, gap="medium")

    with p1:
        st.markdown("**How this park compares**")
        fig_d = go.Figure()
        fig_d.add_trace(go.Box(
            y=sessions["species_per_session"], name="All parks",
            marker_color=theme.MUTED, boxmean=True,
            hovertemplate="%{y} species<extra></extra>",
        ))
        fig_d.add_trace(go.Box(
            y=p_sessions["species_per_session"], name=code,
            marker_color=theme.FOREST, boxmean=True,
            hovertemplate="%{y} species<extra></extra>",
        ))
        fig_d.update_layout(
            yaxis_title="species per session",
            **theme.plotly_layout(height=280, showlegend=False),
        )
        st.plotly_chart(fig_d, width='stretch', config=theme.PLOTLY_CONFIG)

    with p2:
        st.markdown("**Most-recorded species here**")
        top = (p_birds["Common_Name"].value_counts().head(8)
               .sort_values(ascending=True))
        at_risk_names = set(
            p_birds.loc[p_birds["is_at_risk"], "Common_Name"].unique())
        fig_t = go.Figure(go.Bar(
            y=top.index, x=top.values, orientation="h",
            marker_color=[theme.AT_RISK if n in at_risk_names else theme.FOREST
                          for n in top.index],
            hovertemplate="%{y}<br>%{x} sightings<extra></extra>",
        ))
        fig_t.update_layout(
            xaxis_title="sightings",
            **theme.plotly_layout(height=280, showlegend=False),
        )
        st.plotly_chart(fig_t, width='stretch', config=theme.PLOTLY_CONFIG)

    with p3:
        st.markdown("**Effort through the season**")
        by_month = (p_sessions.groupby(["month_name", "habitat"]).size()
                    .unstack(fill_value=0)
                    .reindex([m for m in ["May", "June", "July"]
                              if m in p_sessions["month_name"].unique()]))
        fig_m = go.Figure()
        for hab, colour in theme.HABITAT_COLOURS.items():
            if hab in by_month.columns:
                fig_m.add_bar(name=hab, x=by_month.index, y=by_month[hab],
                              marker_color=colour)
        fig_m.update_layout(
            barmode="stack", yaxis_title="sessions",
            **theme.plotly_layout(height=280),
        )
        st.plotly_chart(fig_m, width='stretch', config=theme.PLOTLY_CONFIG)

    habitats = ", ".join(sorted(p_sessions["habitat"].unique()))
    shared_note = (
        "surveyed in both habitats, so it contributes to every habitat "
        "comparison on this dashboard"
        if bool(p_sessions["is_shared_park"].iloc[0])
        else "surveyed in one habitat only, so it cannot contribute to any "
             "habitat comparison (guardrail G2)"
    )
    st.markdown(
        theme.caption(
            f"{park['park_name']} ran {int(park['sessions_run']):,} sessions "
            f"across {p_sessions['Plot_Name'].nunique()} plots, recording "
            f"{p_birds['Scientific_Name'].nunique()} species in {habitats}. "
            f"It was {shared_note}."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. the proof
st.subheader("Why raw species counts can't rank parks")

pk = q3["parks_by_rate"].reset_index().merge(
    coords[["Admin_Unit_Code", "park_name"]], on="Admin_Unit_Code"
)

# Same spearmanr implementation analysis.py uses, so the method matches the
# rest of the project exactly - this is not a second, different statistic.
rho_raw, p_raw = sh.spearmanr(
    pk["sessions_run"].values, pk["distinct_species"].values
)
rho_rate, p_rate = sh.spearmanr(
    pk["sessions_run"].values, pk["species_per_session"].values
)
# analysis.py rounds every rho it reports to 3 dp - match that, so the same
# statistic never shows up at two different precisions across the dashboard.
rho_raw, rho_rate = round(rho_raw, 3), round(rho_rate, 3)


def _effort_scatter(ycol: str, ylabel: str, colour: str, rho: float, p: float):
    f = go.Figure(go.Scatter(
        x=pk["sessions_run"], y=pk[ycol], mode="markers",
        marker={"size": 12, "color": colour,
                "line": {"width": 1, "color": "#ffffff"}},
        customdata=pk[["park_name"]],
        hovertemplate="<b>%{customdata[0]}</b><br>"
                      "%{x} sessions<br>"
                      f"{ylabel}: " + "%{y}<extra></extra>",
    ))
    f.update_layout(
        xaxis_title="sessions run (survey effort)",
        yaxis_title=ylabel,
        **theme.plotly_layout(height=320, showlegend=False),
    )
    verdict = "significant" if p < 0.05 else "not significant"
    f.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98,
        showarrow=False, align="left",
        text=f"<b>rho = {rho}</b><br>p = {p:.3g} ({verdict})",
        font={"size": 12, "color": theme.INK},
        bgcolor="rgba(255,255,255,0.85)", borderpad=6,
    )
    return f


c0, c1 = st.columns(2, gap="large")

with c0:
    st.markdown("**Raw species count vs effort**")
    st.plotly_chart(
        _effort_scatter("distinct_species", "distinct species",
                        theme.AT_RISK, rho_raw, p_raw),
        width='stretch', config=theme.PLOTLY_CONFIG,
    )
    st.markdown(
        theme.caption(
            "Points climb left to right. A park that was visited more found "
            "more species - which is what you would expect even if every "
            "park were identical."
        ),
        unsafe_allow_html=True,
    )

with c1:
    st.markdown("**Species per session vs effort**")
    st.plotly_chart(
        _effort_scatter("species_per_session", "species per session",
                        theme.FOREST, rho_rate, p_rate),
        width='stretch', config=theme.PLOTLY_CONFIG,
    )
    st.markdown(
        theme.caption(
            "No slope worth reading. Once effort is divided out, how often a "
            "park was visited tells you nothing about how rich it is - which "
            "is exactly the property a fair ranking needs."
        ),
        unsafe_allow_html=True,
    )

st.markdown(
    theme.guardrail_banner(
        f"<b>This is guardrail G1, shown rather than asserted.</b> Raw species "
        f"count correlates with survey effort at rho = {rho_raw} "
        f"(p = {p_raw:.3g}) - strong and significant. The effort-adjusted rate "
        f"correlates at rho = {rho_rate} (p = {p_rate:.3g}) - nothing. So a "
        f"\"most species found\" leaderboard is substantially a leaderboard of "
        f"who got surveyed most, and every ranking on this dashboard uses the "
        f"rate instead."
    ),
    unsafe_allow_html=True,
)

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. ranking
st.subheader("Same parks, different podium")

rank_df = pk.copy()
rank_df["rank_by_rate"] = rank_df["species_per_session"].rank(
    ascending=False, method="min"
).astype(int)
rank_df["rank_by_richness"] = rank_df["distinct_species"].rank(
    ascending=False, method="min"
).astype(int)
rank_df["moved"] = rank_df["rank_by_rate"] - rank_df["rank_by_richness"]
rank_df = rank_df.sort_values("rank_by_rate")

c2, c3 = st.columns([0.6, 0.4], gap="large")

with c2:
    fig = go.Figure()
    for _, row in rank_df.iterrows():
        colour = theme.AT_RISK if abs(row["moved"]) >= 4 else theme.MUTED
        fig.add_trace(go.Scatter(
            x=["Ranked by rate", "Ranked by raw richness"],
            y=[row["rank_by_rate"], row["rank_by_richness"]],
            mode="lines+markers",
            line={"color": colour, "width": 1.6},
            marker={"size": 8, "color": colour},
            showlegend=False,
            hovertemplate=f"{row['park_name']}<extra></extra>",
        ))
    fig.update_yaxes(autorange="reversed", title="rank (1 = top)", dtick=1)
    fig.update_layout(**theme.plotly_layout(height=380, showlegend=False))
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Only Chesapeake &amp; Ohio Canal lands in the same spot on both "
            "sides - every other park's rank shifts at least one place. Red "
            "lines are the three that swing by 5 or more: Wolf Trap ranks #4 "
            "by rate but falls to #11 by raw count, while Monocacy and "
            "Manassas swing the other way, from #6/#7 by rate up to #1/#2 by "
            "raw count."
        ),
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        theme.guardrail_banner(
            "<b>This chart is the scatter above, applied.</b> Monocacy looks "
            "like the #1 hotspot by raw species count and drops to #6 once "
            "effort is accounted for - it wasn't the best park, it was the "
            "third most visited. Wolf Trap moves the opposite way for the "
            "same reason, though with 12 sessions its rate is a rough "
            "estimate rather than a result."
        ),
        unsafe_allow_html=True,
    )
    movers = rank_df[rank_df["moved"] != 0].copy()
    movers = movers.reindex(
        movers["moved"].abs().sort_values(ascending=False).index
    )[
        ["park_name", "rank_by_rate", "rank_by_richness"]
    ].rename(columns={
        "park_name": "Park",
        "rank_by_rate": "Rank (rate)",
        "rank_by_richness": "Rank (raw)",
    })
    st.dataframe(movers, width='stretch', hide_index=True)

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. at-risk
st.subheader("The best park depends on which question you asked")

ar = (
    sessions.groupby("Admin_Unit_Code")
    .agg(sessions_run=("session_id", "size"),
         at_risk_sessions=("has_at_risk", "sum"))
    .reset_index()
)
ar["pct"] = (ar["at_risk_sessions"] / ar["sessions_run"] * 100).round(1)
ar["reliable"] = ar["sessions_run"] >= RELIABLE_FLOOR
ar = ar.merge(coords[["Admin_Unit_Code", "park_name"]], on="Admin_Unit_Code")
ar = ar.merge(pk[["Admin_Unit_Code", "species_per_session"]],
              on="Admin_Unit_Code")
ar["rank_rate"] = ar["species_per_session"].rank(
    ascending=False, method="min"
).astype(int)
ar = ar.sort_values("pct")

c4, c5 = st.columns([0.58, 0.42], gap="large")

with c4:
    fig = go.Figure(go.Bar(
        y=ar["park_name"], x=ar["pct"], orientation="h",
        marker_color=[
            theme.AT_RISK if ok else theme.MUTED for ok in ar["reliable"]
        ],
        text=ar["pct"].map(lambda v: f"{v}%"), textposition="outside",
        customdata=ar[["sessions_run", "rank_rate"]],
        hovertemplate="<b>%{y}</b><br>%{x}% of sessions recorded an "
                      "at-risk bird<br>%{customdata[0]} sessions<br>"
                      "ranks #%{customdata[1]} of 11 for species per session"
                      "<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="% of sessions that recorded at least one at-risk species",
        **theme.plotly_layout(height=400, showlegend=False),
    )
    fig.update_xaxes(range=[0, ar["pct"].max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"A per-session rate, not a raw count, so this is comparable "
            f"across parks of very different effort (guardrail G1). Grey bars "
            f"ran under {RELIABLE_FLOOR} sessions - Rock Creek and Wolf Trap - "
            f"so read those two as rough."
        ),
        unsafe_allow_html=True,
    )

with c5:
    top_ar = ar.sort_values("pct", ascending=False).iloc[0]
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:2.4rem;font-weight:800;color:{theme.AT_RISK};line-height:1">
      {top_ar['pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      of sessions at {top_ar['park_name']} recorded an at-risk species
  </div>
  <div style="font-size:0.95rem;color:{theme.INK};line-height:1.7">
      That is the highest of any park - and the same park ranks
      <b>#{int(top_ar['rank_rate'])} of 11</b> for species per session, dead
      last on the diversity measure.
  </div>
  <div style="margin-top:14px;font-size:0.88rem;color:{theme.INK2};line-height:1.65">
      A birdwatcher wanting the longest list and a manager protecting
      declining species would be sent to opposite ends of this dashboard.
      "Best park" is not a property of a park - it is a property of the
      question, and a single ranking that hides that is doing the reader a
      disservice.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. plots
st.subheader("The individual-plot leaderboard is mostly noise")

plot_stats = (
    sessions.groupby("Plot_Name")
    .species_per_session.agg(["mean", "size"])
    .rename(columns={"mean": "species_per_session", "size": "visits"})
)
top_plots = q3["top_plots"].reset_index().head(15)
top_plots.columns = ["Plot", "Park", "Habitat", "Species per session", "Visits"]
cutoff = top_plots["Species per session"].min()

c6, c7 = st.columns([0.52, 0.48], gap="large")

with c6:
    st.dataframe(top_plots, width='stretch', hide_index=True, height=430)

with c7:
    fig = go.Figure(go.Histogram(
        x=plot_stats["species_per_session"],
        nbinsx=32, marker_color=theme.SEQUENTIAL[3],
        hovertemplate="%{x} species / session<br>%{y} plots<extra></extra>",
    ))
    fig.add_vline(
        x=cutoff, line_width=2, line_dash="dash", line_color=theme.AT_RISK,
        annotation_text="  top 15 →", annotation_position="top",
        annotation_font={"color": theme.AT_RISK, "size": 11},
    )
    fig.update_layout(
        xaxis_title="mean species per session, one bar per plot",
        yaxis_title="number of plots",
        **theme.plotly_layout(height=430, showlegend=False),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)

st.markdown(
    theme.guardrail_banner(
        f"<b>Read the Visits column, then look at the spread.</b> All "
        f"{len(plot_stats)} surveyed plots average "
        f"{plot_stats['species_per_session'].mean():.1f} species per session, "
        f"and the table on the left is simply everything past "
        f"{cutoff} - the right tail of that curve. No plot in the dataset was "
        f"visited more than {int(plot_stats['visits'].max())} times and most "
        f"only twice, so one unusually good morning is enough to land a plot "
        f"at the top. This is guardrail G3 at the smallest scale the data "
        f"supports: park-level numbers need {RELIABLE_FLOOR}+ sessions to "
        f"trust, and a single plot never gets close."
    ),
    unsafe_allow_html=True,
)