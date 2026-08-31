"""
Species - habitat specialists, the at-risk roster, and a searchable table.

Layout, top to bottom:
  1. title
  2. habitat specialists - among the 48 well-sampled species (shared parks
     only), how many are grassland specialists, forest specialists, or
     generalists. The headline: forest produces zero specialists.
  3. the at-risk roster - all 8 watchlist species, dominated by Wood Thrush
  4. exclusive species, raw vs rarefied - why "grassland has 5x more unique
     species" is mostly an artefact of running 4x more sessions
  5. a searchable species table for browsing the full 114
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import theme

res = da.results()
q4, q5, q11 = res["q4"], res["q5"], res["q11"]
species = da.species()
birds = da.birds()
q13 = res["q13"]

# ------------------------------------------------------------------ 1. title
st.title("Species")
st.markdown(
    theme.caption(
        "Habitat preference is scored in the 4 shared parks only, so a "
        "species isn't called a \"specialist\" just because it happened to be "
        "surveyed somewhere with only one habitat type."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------------ 2. specialists
st.subheader("Forest produces zero habitat specialists")

c1, c2 = st.columns([0.5, 0.5], gap="large")

with c1:
    cats = ["Grassland specialist", "Generalist", "Forest specialist"]
    vals = [q4["n_grassland"], q4["n_generalist"], q4["n_forest"]]
    colors = [theme.GRASSLAND, theme.MUTED, theme.FOREST]
    fig = go.Figure(
        go.Bar(
            y=cats, x=vals, orientation="h", marker_color=colors,
            text=vals, textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title=f"species (of {q4['n_well_sampled']} well-sampled)",
        **theme.plotly_layout(height=240, showlegend=False),
    )
    fig.update_xaxes(range=[0, max(vals) * 1.3])
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"{q4['n_well_sampled']} species had enough sightings in shared "
            f"parks to classify. A species needs &gt;80% of its sightings in "
            f"one habitat to count as a specialist there - otherwise it's a "
            f"generalist."
        ),
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        theme.guardrail_banner(
            "<b>Reading this.</b> Every grassland-associated species that was "
            "seen often enough to judge - sparrows, swallows, meadowlark, "
            "bluebird - turned out to be strongly grassland-loyal. Not one "
            "well-sampled species showed that same loyalty to forest; forest "
            "birds in this dataset are generalists that also use grassland. "
            "That's a real ecological asymmetry, not a sampling artefact - it "
            "survives the same shared-parks restriction as every other "
            "number on this dashboard."
        ),
        unsafe_allow_html=True,
    )
    top_specialists = (
        species[species["specialist_class"] == "Grassland specialist"]
        .sort_values("grassland_share_pct", ascending=False)
        .head(6)[["Common_Name", "grassland_share_pct", "total_sightings"]]
    )
    st.dataframe(
        top_specialists.rename(columns={
            "Common_Name": "Species",
            "grassland_share_pct": "% in grassland",
            "total_sightings": "Sightings",
        }),
        width='stretch', hide_index=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 3. at-risk
st.subheader("The at-risk roster: one species carries the other seven")

c3, c4 = st.columns([0.55, 0.45], gap="large")

with c3:
    sp5 = q5["species_profile"].reset_index()
    sp5 = sp5.sort_values("total", ascending=True)
    fig = go.Figure()
    fig.add_bar(
        name="Forest", y=sp5["Common_Name"], x=sp5["Forest"],
        orientation="h", marker_color=theme.FOREST,
    )
    fig.add_bar(
        name="Grassland", y=sp5["Common_Name"], x=sp5["Grassland"],
        orientation="h", marker_color=theme.GRASSLAND,
    )
    fig.update_layout(
        barmode="stack",
        xaxis_title="at-risk sightings (all 11 parks)",
        **theme.plotly_layout(height=340),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            "All 11 parks, not just the 4 shared ones - this chart is about "
            "which species carry the at-risk signal, not a habitat comparison."
        ),
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-radius:14px;padding:20px 22px;height:100%">
  <div style="font-size:2.4rem;font-weight:800;color:{theme.AT_RISK};line-height:1">
      {q5['dominant_share_pct']}%</div>
  <div style="font-size:0.82rem;color:{theme.MUTED};margin-bottom:14px">
      of all {q5['n_sightings']} at-risk sightings are {q5['dominant_species']}
  </div>
  <div style="font-size:0.9rem;color:{theme.INK2};line-height:1.7">
      Of {q5['n_species']} PIF Watchlist species recorded, {q5['dominant_species']}
      alone accounts for most of the signal. Worm-eating Warbler and Prairie
      Warbler are a distant second and third; the remaining five species
      combine for under 3% of at-risk sightings.<br/><br/>
      This is why the Overview headline is written about one species, not
      "at-risk birds" as a category - the category is really one bird plus a
      long tail.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 4. exclusive
st.subheader("\"Grassland has more unique species\" - mostly an effort effect")

c5, c6 = st.columns([0.55, 0.45], gap="large")

with c5:
    fig = go.Figure()
    fig.add_bar(
        name="Forest-only", x=["Raw count", "Rarefied estimate"],
        y=[q11["raw"]["forest_only"], q11["rarefied"]["forest_only"]],
        marker_color=theme.FOREST,
        text=[q11["raw"]["forest_only"], q11["rarefied"]["forest_only"]],
        textposition="outside",
    )
    fig.add_bar(
        name="Grassland-only", x=["Raw count", "Rarefied estimate"],
        y=[q11["raw"]["grassland_only"], q11["rarefied"]["grassland_only"]],
        marker_color=theme.GRASSLAND,
        text=[q11["raw"]["grassland_only"], q11["rarefied"]["grassland_only"]],
        textposition="outside",
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="species seen only in that habitat",
        **theme.plotly_layout(height=320),
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Grassland ran {q11['sessions']['grassland']} sessions against "
            f"forest's {q11['sessions']['forest']} - a "
            f"{q11['sessions']['ratio']}x gap. Rarefaction repeatedly "
            f"resamples grassland down to forest's sample size "
            f"({q11['n_draws']} draws) before counting, which is why the two "
            f"estimates move so much closer together."
        ),
        unsafe_allow_html=True,
    )

with c6:
    st.markdown(
        theme.guardrail_banner(
            f"<b>Guardrail G4.</b> {q11['caveat']} Raw counts say grassland "
            f"has {q11['raw']['grassland_only'] / q11['raw']['forest_only']:.1f}x "
            f"more exclusive species than forest. Rarefied, that gap shrinks to "
            f"{q11['rarefied']['grassland_only'] / q11['rarefied']['forest_only']:.1f}x "
            f"- still real, just far smaller than the raw number implies."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            f"{q11['seen_once_only']['forest_only']} of the forest-only "
            f"species and {q11['seen_once_only']['grassland_only']} of the "
            f"grassland-only species were seen exactly once - a single extra "
            f"sighting could move them into the shared column, so treat the "
            f"raw counts as fragile even before rarefaction."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

st.write("")
st.divider()

# ------------------------------------------------------------------ 5. structure
st.subheader("Two communities with the same shape and different occupants")

shared_rows = birds[birds.is_shared_park]

r1, r2 = st.columns([0.55, 0.45], gap="large")

with r1:
    st.markdown("**Rank-abundance curves**")
    fig = go.Figure()
    stats = {}
    for hab, colour in theme.HABITAT_COLOURS.items():
        counts = shared_rows[shared_rows.habitat == hab] \
            .Scientific_Name.value_counts()
        share = (counts / counts.sum() * 100)
        names = [
            species.set_index("Scientific_Name")["Common_Name"].get(n, n)
            for n in counts.index
        ]
        stats[hab] = {
            "n": len(counts),
            "top5": round(float(share.head(5).sum()), 1),
            "singletons": int((counts == 1).sum()),
        }
        fig.add_trace(go.Scatter(
            x=list(range(1, len(share) + 1)), y=share.values,
            mode="lines", name=hab,
            line={"color": colour, "width": 2.4},
            customdata=names,
            hovertemplate="rank %{x}: %{customdata}<br>"
                          "%{y:.2f}% of sightings<extra></extra>",
        ))
    fig.update_layout(
        xaxis_title="species rank (most to least recorded)",
        yaxis_title="% of that habitat's sightings",
        **theme.plotly_layout(height=350),
    )
    fig.update_yaxes(type="log")
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"Log scale, shared parks only. The two curves lie almost on top "
            f"of one another - the top five species take "
            f"{stats['Forest']['top5']}% of forest sightings against "
            f"{stats['Grassland']['top5']}% in grassland. Both communities "
            f"are dominated to the same degree, which is the evenness result "
            f"from the Habitat page drawn out species by species."
        ),
        unsafe_allow_html=True,
    )

with r2:
    st.markdown(
        theme.guardrail_banner(
            f"<b>Same shape, different occupants.</b> Identical curves do not "
            f"mean identical communities - the axis is rank, not identity. "
            f"Grassland's curve is longer "
            f"({stats['Grassland']['n']} species against "
            f"{stats['Forest']['n']}) mostly because it ran more sessions, "
            f"and its tail holds more singletons "
            f"({stats['Grassland']['singletons']} against "
            f"{stats['Forest']['singletons']}). What differs between the two "
            f"habitats is <i>which</i> species occupy each rank, which is "
            f"precisely what the Bray-Curtis figure measures and the Jaccard "
            f"figure cannot see."
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        theme.caption(
            "A rank-abundance curve is the standard way ecologists show "
            "community structure: a steep curve means a few species dominate, "
            "a shallow one means abundance is spread evenly. Reading the two "
            "together is what separates \"how the community is organised\" "
            "from \"who is in it\"."
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ------------------------------------------------------------------ 6. landscape
st.subheader("Every well-sampled species, placed by loyalty and abundance")

ws = species[species["well_sampled"]].copy()
CLASS_COLOUR = {
    "Grassland specialist": theme.GRASSLAND,
    "Forest specialist": theme.FOREST,
    "Generalist": theme.MUTED,
}

g1, g2 = st.columns([0.62, 0.38], gap="large")

with g1:
    fig = go.Figure()
    for cls, colour in CLASS_COLOUR.items():
        sub = ws[ws["specialist_class"] == cls]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["grassland_share_pct"], y=sub["total_sightings"],
            mode="markers", name=f"{cls} ({len(sub)})",
            marker={
                "size": 11, "color": colour,
                "line": {"width": 1.4,
                         "color": [theme.AT_RISK if r else "#ffffff"
                                   for r in sub["is_at_risk"]]},
            },
            customdata=sub[["Common_Name", "forest_sightings",
                            "grassland_sightings", "is_at_risk"]],
            hovertemplate="<b>%{customdata[0]}</b><br>"
                          "%{x}% of sightings in grassland<br>"
                          "forest %{customdata[1]} / grassland %{customdata[2]}"
                          "<br>at-risk: %{customdata[3]}<extra></extra>",
        ))
    for x in (20, 80):
        fig.add_vline(x=x, line_width=1, line_dash="dot",
                      line_color=theme.BORDER)
    fig.update_layout(
        xaxis_title="% of sightings in grassland  (0 = forest-loyal, 100 = grassland-loyal)",
        yaxis_title="total sightings",
        **theme.plotly_layout(height=400),
    )
    fig.update_yaxes(type="log")
    # Pin the full 0-100 range. Left to itself the axis starts around 28%,
    # which crops away the empty forest-specialist zone - and that emptiness
    # is the whole point of the chart.
    fig.update_xaxes(range=[0, 100], dtick=20)
    fig.add_annotation(
        x=10, y=0.97, xref="x", yref="paper", showarrow=False,
        text="<i>forest specialists<br>would sit here</i>",
        font={"size": 10, "color": theme.MUTED}, align="center",
    )
    st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
    st.markdown(
        theme.caption(
            f"All {len(ws)} well-sampled species at once. Dotted lines mark "
            f"the 20% and 80% specialist thresholds. Red-ringed points are "
            f"PIF Watchlist species. Log scale on abundance, because the "
            f"commonest species outnumbers the rarest well-sampled one many "
            f"times over."
        ),
        unsafe_allow_html=True,
    )

with g2:
    st.markdown(
        theme.guardrail_banner(
            f"<b>Read the left edge.</b> The forest-specialist zone - below "
            f"20% - is empty. Every well-sampled species either favours "
            f"grassland strongly or sits in the generalist band, and the "
            f"emptiness of that corner is the finding from the top of this "
            f"page, shown as an absence rather than a zero in a table."
        ),
        unsafe_allow_html=True,
    )
    edge = ws.nsmallest(5, "grassland_share_pct")[
        ["Common_Name", "grassland_share_pct", "total_sightings"]
    ].rename(columns={"Common_Name": "Species",
                      "grassland_share_pct": "% grassland",
                      "total_sightings": "Sightings"})
    st.markdown(
        theme.caption("The five most forest-leaning species, none of which "
                      "clears the specialist threshold:"),
        unsafe_allow_html=True,
    )
    st.dataframe(edge, width='stretch', hide_index=True)

st.write("")
st.divider()

# ------------------------------------------------------------------ 7. dumbbell
st.subheader("Where the weighting difference shows up, species by species")

top_n = 18
dumb = ws.nlargest(top_n, "total_sightings").copy()
tot = dumb["forest_sightings"] + dumb["grassland_sightings"]
dumb["forest_pct"] = (dumb["forest_sightings"] / tot * 100).round(1)
dumb["grassland_pct"] = (dumb["grassland_sightings"] / tot * 100).round(1)
dumb = dumb.sort_values("grassland_pct")

fig = go.Figure()
for _, row in dumb.iterrows():
    fig.add_trace(go.Scatter(
        x=[row["forest_pct"], row["grassland_pct"]],
        y=[row["Common_Name"], row["Common_Name"]],
        mode="lines", line={"color": theme.BORDER, "width": 2.5},
        showlegend=False, hoverinfo="skip",
    ))
fig.add_trace(go.Scatter(
    x=dumb["forest_pct"], y=dumb["Common_Name"], mode="markers", name="Forest",
    marker={"size": 11, "color": theme.FOREST},
    customdata=dumb[["forest_sightings"]],
    hovertemplate="<b>%{y}</b><br>%{x}% of its sightings in forest<br>"
                  "%{customdata[0]} records<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=dumb["grassland_pct"], y=dumb["Common_Name"], mode="markers",
    name="Grassland", marker={"size": 11, "color": theme.GRASSLAND},
    customdata=dumb[["grassland_sightings"]],
    hovertemplate="<b>%{y}</b><br>%{x}% of its sightings in grassland<br>"
                  "%{customdata[0]} records<extra></extra>",
))
fig.add_vline(x=50, line_width=1, line_dash="dot", line_color=theme.MUTED)
fig.update_layout(
    xaxis_title="% of that species' sightings, forest against grassland",
    **theme.plotly_layout(height=520),
)
st.plotly_chart(fig, width='stretch', config=theme.PLOTLY_CONFIG)
st.markdown(
    theme.caption(
        f"The {top_n} most-recorded well-sampled species. A long bar means a "
        f"species is used very unevenly by the two habitats; a short one "
        f"means it is genuinely indifferent. The dotted line is an even "
        f"split. This is the abundance-weighting difference from the Habitat "
        f"page at the level of individual birds - most of these species "
        f"appear in both habitats, which is why species lists look similar, "
        f"and lean heavily to one side, which is why abundance profiles do "
        f"not."
    ),
    unsafe_allow_html=True,
)

st.write("")
st.divider()

# ------------------------------------------------------------------ 8. explorer
st.subheader("Species explorer")

f1, f2, f3 = st.columns([0.4, 0.3, 0.3])
with f1:
    query = st.text_input("Search by name", placeholder="e.g. sparrow, warbler")
with f2:
    class_filter = st.multiselect(
        "Habitat class",
        options=sorted(species["specialist_class"].unique()),
    )
with f3:
    at_risk_only = st.checkbox("At-risk only")

table = species.copy()
if query:
    table = table[table["Common_Name"].str.contains(query, case=False, na=False)]
if class_filter:
    table = table[table["specialist_class"].isin(class_filter)]
if at_risk_only:
    table = table[table["is_at_risk"]]

st.dataframe(
    table[[
        "Common_Name", "specialist_class", "is_at_risk",
        "forest_sightings", "grassland_sightings", "total_sightings",
    ]].rename(columns={
        "Common_Name": "Species",
        "specialist_class": "Habitat class",
        "is_at_risk": "At-risk",
        "forest_sightings": "Forest",
        "grassland_sightings": "Grassland",
        "total_sightings": "Total",
    }).sort_values("Total", ascending=False),
    width='stretch', hide_index=True, height=380,
)
st.markdown(
    theme.caption(
        f"Showing {len(table)} of {len(species)} species scored in the 4 "
        f"shared parks. Sightings here are shared-parks-only, so they won't "
        f"match the all-parks counts in the at-risk chart above."
    ),
    unsafe_allow_html=True,
)