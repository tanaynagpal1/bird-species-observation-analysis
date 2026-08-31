"""
Habitat Comparison - the page that teaches Simpson's paradox by showing it
happen to our own numbers, live.

Layout, top to bottom:
  1. title
  2. the paradox: pooled (all 11 parks) says "significant difference",
     within the 4 shared parks it vanishes
  3. why: a per-park breakdown - 2 parks favour forest, 2 favour grassland,
     so the pooled average is really tracking which parks got more forest
     sessions, not habitat quality
  4. the contrast: the at-risk finding from Overview does NOT collapse the
     same way - it holds in all 4 shared parks - so the page ends by drawing
     the line between a real finding and a confounded one
  5. guardrail note
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q1, q2, q13 = res["q1"], res["q2"], res["q13"]
sessions = da.sessions()

PARK_NAME = {
    "ANTI": "Antietam",
    "HAFE": "Harpers Ferry",
    "MANA": "Manassas",
    "MONO": "Monocacy",
}

# ------------------------------------------------------------------ 1. title
st.title("Habitat Comparison")
st.markdown(
    theme.caption(
        "This page always compares the 4 parks surveyed in <b>both</b> habitats, "
        "regardless of the sidebar filters - that is guardrail G2, and it is the "
        "whole point of this page."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. paradox
st.subheader("A finding that only exists if you pool the data wrong")

left, right = st.columns([0.46, 0.54], gap="large")

with left:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:10px">
      Pooling all 11 parks</div>
  <div style="font-size:1.05rem;color:{theme.INK};line-height:1.7">
      Forest averages <b>{q2['pooled']['forest']}</b> species per session against
      <b>{q2['pooled']['grassland']}</b> in grassland.<br/>
      p = {q2['pooled']['p_value']:.1e} &nbsp;→&nbsp;
      <b style="color:{theme.AT_RISK}">looks significant</b>
  </div>
  <div style="height:1px;background:{theme.BORDER};margin:16px 0"></div>
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:10px">
      Within the 4 shared parks only</div>
  <div style="font-size:1.05rem;color:{theme.INK};line-height:1.7">
      Forest <b>{q2['within_shared']['forest']}</b> vs grassland
      <b>{q2['within_shared']['grassland']}</b> - nearly identical.<br/>
      p = {q2['within_shared']['p_value']:.2f} &nbsp;→&nbsp;
      <b style="color:{theme.FOREST}">nothing there</b>
  </div>
  <div style="margin-top:16px;font-size:0.88rem;color:{theme.INK2};line-height:1.6">
      Same data. The "finding" disappears the moment the comparison is made
      fair. This is <b>Simpson's paradox</b>: pooling groups of very different
      sizes and compositions can manufacture a pattern that isn't really there.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with right:
    fig = go.Figure()
    cats = ["Pooled (11 parks)", "Shared parks only (4)"]
    fig.add_bar(
        name="Forest", x=cats,
        y=[q2["pooled"]["forest"], q2["within_shared"]["forest"]],
        marker_color=theme.FOREST,
        text=[q2["pooled"]["forest"], q2["within_shared"]["forest"]],
        textposition="outside",
    )
    fig.add_bar(
        name="Grassland", x=cats,
        y=[q2["pooled"]["grassland"], q2["within_shared"]["grassland"]],
        marker_color=theme.GRASSLAND,
        text=[q2["pooled"]["grassland"], q2["within_shared"]["grassland"]],
        textposition="outside",
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="species per session",
        **theme.plotly_layout(height=300),
    )
    fig.update_yaxes(range=[0, 11])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Pooled: n={q2['pooled']['n_forest']} forest sessions vs "
            f"{q2['pooled']['n_grassland']} grassland. Within shared parks: "
            f"n={q2['within_shared']['n_forest']} vs "
            f"{q2['within_shared']['n_grassland']} - forest has far fewer "
            f"sessions either way, which is exactly why G1 (rates, not counts) "
            f"and G2 (shared parks only) both matter here."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. why
st.subheader("Why pooling misleads: it's really comparing parks, not habitats")

c1, c2 = st.columns([0.58, 0.42], gap="large")

with c1:
    bp = q2["by_park"].rename(index=PARK_NAME)
    fig = go.Figure()
    fig.add_bar(
        name="Forest", x=bp.index, y=bp["Forest"],
        marker_color=theme.FOREST, text=bp["Forest"], textposition="outside",
    )
    fig.add_bar(
        name="Grassland", x=bp.index, y=bp["Grassland"],
        marker_color=theme.GRASSLAND, text=bp["Grassland"], textposition="outside",
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="species per session",
        **theme.plotly_layout(height=340),
    )
    fig.update_yaxes(range=[0, bp[["Forest", "Grassland"]].values.max() * 1.25])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"{q2['parks_favouring_forest']} of {q2['n_parks']} parks favour "
            f"forest, the other {q2['n_parks'] - q2['parks_favouring_forest']} "
            f"favour grassland. There is no consistent winner - the pooled "
            f"number is an average of a genuine split, not a real effect."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        theme.guardrail_banner(
            "<b>Reading this chart.</b> If forest genuinely supported more "
            "species, it should win in most or all of these four parks. It "
            "wins in exactly half. That is the signature of noise, not a "
            "habitat effect - and it is why guardrail G2 restricts every "
            "habitat comparison on this dashboard to parks surveyed in both "
            "habitats."
        ),
        unsafe_allow_html=True,
    )
    st.dataframe(
        q2["by_park"].rename(index=PARK_NAME).rename(
            columns={"forest_higher": "Forest wins"}
        ),
        width='stretch',
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. contrast
st.subheader("Not every habitat claim collapses this way")

c3, c4 = st.columns([0.42, 0.58], gap="large")

with c3:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:1.05rem;color:{theme.INK};line-height:1.7">
      The <b>at-risk species</b> finding from Overview is built the same
      way - shared parks only - and it does <i>not</i> fall apart.
  </div>
  <div style="margin-top:12px;font-size:0.9rem;color:{theme.INK2};line-height:1.65">
      Forest sessions record at-risk birds at <b>{q1['forest_pct']}%</b> against
      <b>{q1['grassland_pct']}%</b> in grassland
      (p = {q1['p_value']:.1e}), and forest wins in
      <b>all {q1['n_parks']} of {q1['n_parks']}</b> shared parks - not a coin
      flip like richness above.
  </div>
  <div style="margin-top:12px;font-size:0.85rem;color:{theme.MUTED};line-height:1.6">
      The difference between these two charts is the difference between a
      confounded correlation and a real one - and the only way to tell them
      apart was to check whether the pattern survives every park, not just
      the average.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with c4:
    bp1 = q1["by_park"].rename(index=PARK_NAME)
    fig = go.Figure()
    fig.add_bar(
        name="Forest", x=bp1.index, y=bp1["Forest"],
        marker_color=theme.FOREST, text=bp1["Forest"], textposition="outside",
    )
    fig.add_bar(
        name="Grassland", x=bp1.index, y=bp1["Grassland"],
        marker_color=theme.GRASSLAND, text=bp1["Grassland"], textposition="outside",
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="% of sightings that are at-risk",
        **theme.plotly_layout(height=300),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption("Forest wins in every single shared park - all four bars point the same way."),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. spread
st.subheader("The same comparison, as distributions")
st.markdown(
    theme.caption(
        "Every chart above reports a mean. Means are what made the pooled "
        "comparison look convincing in the first place, so it is worth seeing "
        "the spread they came from."
    ),
    unsafe_allow_html=True,
)
st.write("")

d1, d2 = st.columns([0.42, 0.58], gap="large")

with d1:
    st.markdown("**Pooled against shared-parks-only**")
    pooled = sessions
    sharedp = sessions[sessions.is_shared_park]
    fig = go.Figure()
    # go.Box has no dashed-outline option, so the two subsets are separated by
    # fill instead: pooled solid, shared-parks hollow.
    for label, frame, filled in (("All 11 parks", pooled, True),
                                 ("Shared parks only", sharedp, False)):
        for hab, colour in theme.HABITAT_COLOURS.items():
            fig.add_trace(go.Box(
                y=frame[frame.habitat == hab]["species_per_session"],
                name=f"{hab}<br>{label}", boxmean=True,
                marker_color=colour,
                fillcolor=colour if filled else "rgba(0,0,0,0)",
                line={"color": colour, "width": 2},
                hovertemplate="%{y} species<extra></extra>",
            ))
    fig.update_layout(
        yaxis_title="species per session",
        **theme.plotly_layout(height=380, showlegend=False),
    )
    fig.update_xaxes(tickfont={"size": 9})
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Hollow boxes are the shared-parks subset. Restricting to it "
            "barely moves grassland but lifts forest onto it - the boxes end "
            "up sitting on top of one another, which is the p-value made "
            "visible."
        ),
        unsafe_allow_html=True,
    )

with d2:
    st.markdown("**Per park, per habitat**")
    sub = sessions[sessions.is_shared_park].copy()
    sub["park"] = sub["Admin_Unit_Code"].map(PARK_NAME).fillna(
        sub["Admin_Unit_Code"])
    fig = go.Figure()
    for hab, colour in theme.HABITAT_COLOURS.items():
        d = sub[sub.habitat == hab]
        fig.add_trace(go.Box(
            x=d["park"], y=d["species_per_session"], name=hab,
            marker_color=colour, boxmean=True,
            hovertemplate="%{x}<br>%{y} species<extra></extra>",
        ))
    fig.update_layout(
        boxmode="group", yaxis_title="species per session",
        **theme.plotly_layout(height=380),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Small multiples of the same test. In every park the two boxes "
            "overlap heavily, and which one sits higher changes from park to "
            "park - the coin flip described above, seen as distributions "
            "rather than as four pairs of bars."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. diversity
st.subheader("Four ways of measuring diversity, one answer")

e1, e2 = st.columns([0.52, 0.48], gap="large")

with e1:
    metrics = q13["metrics"]
    # Each index lives on its own scale, so plot each as % of the larger
    # habitat value - the comparison is the point, not the absolute level.
    labels, f_rel, g_rel, raw = [], [], [], []
    for m in metrics:
        t = q13["tests"][m]
        top = max(t["forest"], t["grassland"])
        labels.append(m.replace("_", " ").title())
        f_rel.append(t["forest"] / top * 100)
        g_rel.append(t["grassland"] / top * 100)
        raw.append((t["forest"], t["grassland"], t["p_value"]))
    fig = go.Figure()
    fig.add_bar(name="Forest", x=labels, y=f_rel, marker_color=theme.FOREST,
                customdata=[r[0] for r in raw],
                hovertemplate="%{x}<br>forest %{customdata}<extra></extra>")
    fig.add_bar(name="Grassland", x=labels, y=g_rel,
                marker_color=theme.GRASSLAND,
                customdata=[r[1] for r in raw],
                hovertemplate="%{x}<br>grassland %{customdata}<extra></extra>")
    fig.update_layout(
        barmode="group",
        yaxis_title="% of the higher habitat value",
        **theme.plotly_layout(height=330),
    )
    fig.update_yaxes(range=[0, 118])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "Scaled to the higher habitat so four different units can share "
            "an axis - hover for the real values. Every pair is within a few "
            "percent of level, and none of the four differences is "
            "significant."
        ),
        unsafe_allow_html=True,
    )

with e2:
    st.markdown(
        theme.guardrail_banner(
            f"<b>The null result is not an artefact of choosing richness.</b> "
            f"Shannon weights rare species, Simpson weights dominant ones, "
            f"and Pielou's evenness divides richness out of the calculation "
            f"altogether. All four reach the same verdict as the plain "
            f"species count did - smallest p = "
            f"{min(t['p_value'] for t in q13['tests'].values()):.2f}. Four "
            f"measures with different sensitivities agreeing is far stronger "
            f"than one measure alone, and it closes off the obvious objection "
            f"that we picked a metric that could not see the difference."
        ),
        unsafe_allow_html=True,
    )
    div_table = pd.DataFrame([
        (m.replace("_", " ").title(), q13["tests"][m]["forest"],
         q13["tests"][m]["grassland"],
         f"{q13['tests'][m]['p_value']:.3f}")
        for m in q13["metrics"]
    ], columns=["Measure", "Forest", "Grassland", "p"])
    st.dataframe(div_table, width='stretch', hide_index=True)

st.write("")
st.divider()

# ------------------------------------------------------------------ 7. composition
st.subheader("Where the habitat difference actually lives")

sim = q13["similarity"]

f1, f2 = st.columns([0.55, 0.45], gap="large")

with f1:
    fig = go.Figure()
    fig.add_bar(
        name="Between habitats, same park",
        x=["Jaccard<br>(species present)", "Bray-Curtis<br>(abundance)"],
        y=[sim["between_habitat"]["jaccard"], sim["between_habitat"]["bray_curtis"]],
        marker_color=theme.AT_RISK,
        text=[sim["between_habitat"]["jaccard"], sim["between_habitat"]["bray_curtis"]],
        textposition="outside",
    )
    fig.add_bar(
        name="Same habitat, different parks",
        x=["Jaccard<br>(species present)", "Bray-Curtis<br>(abundance)"],
        y=[sim["within_habitat"]["jaccard"], sim["within_habitat"]["bray_curtis"]],
        marker_color=theme.MUTED,
        text=[sim["within_habitat"]["jaccard"], sim["within_habitat"]["bray_curtis"]],
        textposition="outside",
    )
    fig.update_layout(
        barmode="group", yaxis_title="similarity / dissimilarity",
        **theme.plotly_layout(height=350),
    )
    fig.update_yaxes(range=[0, 0.78])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Both rarefied to equal session counts over "
            f"{q13['n_draws']} draws. The grey bars are the yardstick: how "
            f"different two parks of the <i>same</i> habitat are. A real "
            f"habitat effect should push the red bar past the grey one."
        ),
        unsafe_allow_html=True,
    )

with f2:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px">
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">
      Species present</div>
  <div style="font-size:1.3rem;font-weight:800;color:{theme.MUTED}">
      {sim['between_habitat']['jaccard']} vs {sim['within_habitat']['jaccard']}
      &nbsp;<span style="font-size:0.85rem;font-weight:600">no real gap</span>
  </div>
  <div style="font-size:0.88rem;color:{theme.INK2};margin-top:6px;line-height:1.6">
      Forest and grassland are no more distinct in <i>which</i> species they
      hold than two parks of the same habitat are.
  </div>
  <div style="height:1px;background:{theme.BORDER};margin:16px 0"></div>
  <div style="font-size:0.82rem;color:{theme.MUTED};font-weight:700;
              text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">
      Abundance structure</div>
  <div style="font-size:1.3rem;font-weight:800;color:{theme.AT_RISK}">
      {sim['between_habitat']['bray_curtis']} vs {sim['within_habitat']['bray_curtis']}
      &nbsp;<span style="font-size:0.85rem;font-weight:600">clear gap</span>
  </div>
  <div style="font-size:0.88rem;color:{theme.INK2};margin-top:6px;line-height:1.6">
      How abundant each species is differs substantially more between
      habitats than between parks.
  </div>
  <div style="margin-top:16px;font-size:0.9rem;color:{theme.INK};line-height:1.7">
      <b>So the habitat effect is real, and it is a weighting effect.</b> The
      two habitats share a species pool and use it differently - which is
      exactly why species counts find nothing while specialist counts and
      at-risk rates do.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown(
    theme.guardrail_banner(
        f"<b>Guardrail G4 again, and it mattered.</b> Before rarefaction the "
        f"between-habitat Bray-Curtis figure read "
        f"{sim['between_habitat']['bray_curtis_raw']} rather than "
        f"{sim['between_habitat']['bray_curtis']}, overstating the gap by "
        f"about {sim['rarefaction_shrank_bray_gap_by_pct']}%. Species-list "
        f"comparisons are among the most effort-sensitive statistics in "
        f"ecology - the finding survives the correction, but it would have "
        f"been badly overstated without it."
    ),
    unsafe_allow_html=True,
)

st.write("")
st.divider()

# ------------------------------------------------------------------ 8. method
with st.expander("What Simpson's paradox is, in one sentence"):
    st.markdown(
        "Pooling data from groups that differ in size or composition can make "
        "a pattern appear (or disappear) that isn't present within any single "
        "group. Here, grassland ran 4x more sessions than forest and the two "
        "habitats weren't surveyed in the same parks - so a pooled average "
        "partly reflects *which parks got surveyed how often*, not habitat "
        "quality. Checking the result **within** each shared park is what "
        "catches it."
    )