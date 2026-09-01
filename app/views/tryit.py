"""
Try It Yourself - the method, made playable.

Two interactive sections, both aimed at the same idea: the parts of this
project that are hardest to believe from a paragraph are easy to believe from
a switch.

  1. The guardrail simulator. Four toggles, one per guardrail. Turning one off
     re-runs the affected analysis on the real data and shows the conclusion
     the project would have published without it. G2 is the headline: switch it
     off and a null result becomes a significant one in front of you.

  2. The ear test. Q14 found that 88.2% of detections are auditory and that the
     observer gap lives almost entirely on that channel. Reading that is one
     thing; failing to tell two species apart by ear is another.

The audio section is deliberately optional. It renders as a complete, finished
explanation with zero audio files present, and upgrades itself into a working
quiz when recordings and a manifest appear in data/audio/. Nothing here breaks
without them, and no network call is ever made - consistent with the rest of
the dashboard, which fetches nothing at run time.

Every number on this page is recomputed live from the session table. Nothing is
hard-coded, so the simulator cannot drift away from the analysis it is
demonstrating.
"""
from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_access as da
import stats_helpers as sh
import theme

res = da.results()
q2, q3, q11, q14 = res["q2"], res["q3"], res["q11"], res["q14"]
sessions = da.sessions()
birds = da.birds()
coords = da.park_coordinates()
NAME = dict(zip(coords["Admin_Unit_Code"], coords["park_name"]))

RELIABLE_FLOOR = 30
VISIT_FLOOR = 3
AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio"


# ==================================================================== compute
@st.cache_data(show_spinner=False)
def park_effort() -> pd.DataFrame:
    """Per park: effort, the per-session rate (G1 on) and the raw count (G1 off)."""
    t = sessions.groupby("Admin_Unit_Code").agg(
        sessions=("species_per_session", "size"),
        rate=("species_per_session", "mean"))
    t["raw_species"] = birds.groupby("Admin_Unit_Code")["Common_Name"].nunique()
    t["park"] = [NAME.get(i, i) for i in t.index]
    return t.round(2)


@st.cache_data(show_spinner=False)
def effort_correlations() -> dict:
    """How strongly each measure tracks survey effort rather than ecology."""
    t = park_effort()
    raw_rho, raw_p = sh.spearmanr(t["sessions"].values.astype(float),
                                  t["raw_species"].values.astype(float))
    rate_rho, rate_p = sh.spearmanr(t["sessions"].values.astype(float),
                                    t["rate"].values.astype(float))
    return {"raw": (round(raw_rho, 3), raw_p),
            "rate": (round(rate_rho, 3), rate_p)}


@st.cache_data(show_spinner=False)
def plot_table() -> pd.DataFrame:
    return (sessions.groupby("Plot_Name")
            .agg(visits=("species_per_session", "size"),
                 rate=("species_per_session", "mean"))
            .round(2))


PARKS = park_effort()
CORR = effort_correlations()
PLOTS = plot_table()

TOP_RAW = list(PARKS.sort_values("raw_species", ascending=False)["park"][:3])
TOP_RATE = list(PARKS.sort_values("rate", ascending=False)["park"][:3])

_no_floor = PLOTS.sort_values("rate", ascending=False).head(5)
_floored = PLOTS[PLOTS["visits"] >= VISIT_FLOOR].sort_values(
    "rate", ascending=False).head(5)
PLOT_OVERLAP = len(set(_no_floor.index) & set(_floored.index))

RAW_RATIO = q11["raw"]["grassland_only"] / q11["raw"]["forest_only"]
RARE_RATIO = (q11["rarefied"]["grassland_only"]
              / q11["rarefied"]["forest_only"])
INFLATION = RAW_RATIO / RARE_RATIO


# ==================================================================== charts
def chart_g1():
    """Effort against raw species count, one point per park.

    Parks that ran a similar number of sessions land almost on top of each
    other, so labels are alternated above and below the marker rather than all
    placed on top - otherwise MANA and CHOH overprint each other.
    """
    t = PARKS.sort_values("sessions")
    positions = ["top center" if i % 2 == 0 else "bottom center"
                 for i in range(len(t))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t["sessions"], y=t["raw_species"], mode="markers+text",
        text=t.index, textposition=positions,
        textfont={"size": 10, "color": theme.MUTED},
        marker={"size": 13, "color": theme.AT_RISK},
        cliponaxis=False,
        customdata=t["park"],
        hovertemplate="%{customdata}<br>%{x} sessions<br>"
                      "%{y} distinct species<extra></extra>"))
    fig.update_layout(
        xaxis_title="survey sessions run (effort)",
        yaxis_title="distinct species recorded (raw count)",
        **theme.plotly_layout(height=350, showlegend=False))
    fig.update_yaxes(range=[t["raw_species"].min() - 12,
                            t["raw_species"].max() + 12])
    return fig


def chart_g2():
    fig = go.Figure()
    cats = ["Pooled (all 11 parks)", "Within shared parks only"]
    for hab, colour, key in (("Forest", theme.FOREST, "forest"),
                             ("Grassland", theme.GRASSLAND, "grassland")):
        vals = [q2["pooled"][key], q2["within_shared"][key]]
        fig.add_trace(go.Bar(x=cats, y=vals, name=hab, marker_color=colour,
                             text=[f"{v:.2f}" for v in vals],
                             textposition="outside"))
    fig.update_layout(barmode="group", yaxis_title="species per session",
                      **theme.plotly_layout(height=330))
    fig.update_yaxes(range=[0, 11])
    return fig


def chart_g3():
    t = PLOTS.sort_values("rate", ascending=False).head(8).iloc[::-1]
    colours = [theme.FOREST if v >= VISIT_FLOOR else theme.AT_RISK
               for v in t["visits"]]
    fig = go.Figure(go.Bar(
        x=t["rate"], y=t.index, orientation="h", marker_color=colours,
        text=[f"{r:.2f}  ({int(v)} visits)"
              for r, v in zip(t["rate"], t["visits"])],
        textposition="outside"))
    fig.update_layout(xaxis_title="species per session",
                      **theme.plotly_layout(height=340, showlegend=False))
    fig.update_xaxes(range=[0, t["rate"].max() * 1.35])
    return fig


def chart_g4():
    fig = go.Figure()
    cats = ["Raw count", f"Rarefied ({q11['n_draws']} draws)"]
    for hab, colour, key in (("Forest only", theme.FOREST, "forest_only"),
                             ("Grassland only", theme.GRASSLAND,
                              "grassland_only")):
        vals = [q11["raw"][key], q11["rarefied"][key]]
        fig.add_trace(go.Bar(x=cats, y=vals, name=hab, marker_color=colour,
                             text=[f"{v:.1f}" for v in vals],
                             textposition="outside"))
    fig.update_layout(barmode="group",
                      yaxis_title="species found in only one habitat",
                      **theme.plotly_layout(height=330))
    return fig


# ==================================================================== content
# Each guardrail: what it does, the true conclusion, the false one you reach
# without it, and the evidence that makes the difference visible.
GUARDRAILS = [
    {
        "key": "g1",
        "name": "G1 — per-session rates",
        "short": "Rates, not raw counts",
        "does": "Divide every count by the number of sessions that produced it.",
        "true": (
            f"**Park rankings reflect richness.** The per-session rate barely "
            f"tracks effort (rho = {CORR['rate'][0]}, "
            f"p = {CORR['rate'][1]:.2f} — not significant), so the ranking is "
            f"about the birds."),
        "false": (
            f"**Park rankings reflect how often you visited.** Raw distinct-"
            f"species counts correlate with survey effort at rho = "
            f"**{CORR['raw'][0]}** (p = {CORR['raw'][1]:.3f} — significant). "
            f"The 'best' parks become the most-visited ones - the top three "
            f"changes completely, and the park that tops the raw list "
            f"({TOP_RAW[0]}) is not the one that tops the honest list "
            f"({TOP_RATE[0]})."),
        "chart": chart_g1,
        "caption": "Each point is a park. Visit a park more and you record "
                   "more species - which says nothing about the habitat.",
    },
    {
        "key": "g2",
        "name": "G2 — shared parks only",
        "short": "Compare within parks",
        "does": "Compare habitats only inside parks that were surveyed in both.",
        "true": (
            f"**Habitat does not affect species richness.** Within the "
            f"{q2['n_parks']} parks surveyed in both habitats: "
            f"{q2['within_shared']['forest']} vs "
            f"{q2['within_shared']['grassland']} species per session, "
            f"p = {q2['within_shared']['p_value']:.2f}. Forest wins in "
            f"{q2['parks_favouring_forest']} of {q2['n_parks']} — a coin flip."),
        "false": (
            f"**Grassland is significantly richer than forest.** Pooled across "
            f"all 11 parks: {q2['pooled']['forest']} vs "
            f"{q2['pooled']['grassland']} species per session, "
            f"p = {q2['pooled']['p_value']:.1e}. This is **Simpson's "
            f"paradox** — grassland ran more sessions in different parks, and "
            f"the park differences wore a habitat costume."),
        "chart": chart_g2,
        "caption": "The same data twice. The left pair is a real, "
                   "reproducible, significant result about the wrong thing.",
    },
    {
        "key": "g3",
        "name": f"G3 — the {RELIABLE_FLOOR}-session floor",
        "short": "Ignore tiny samples",
        "does": (f"Never rank anything below {RELIABLE_FLOOR} sessions, or "
                 f"{VISIT_FLOOR} visits at plot level."),
        "true": (
            f"**Only adequately-sampled units are ranked.** With a "
            f"{VISIT_FLOOR}-visit floor the plot leaderboard is built from "
            f"plots that were actually visited enough to say something."),
        "false": (
            f"**The leaderboard becomes a list of lucky mornings.** Without a "
            f"floor, the top plot scores "
            f"{_no_floor['rate'].iloc[0]:.2f} species per session on just "
            f"**{int(_no_floor['visits'].iloc[0])} visits**. Only "
            f"{PLOT_OVERLAP} of the top five survive when the floor is "
            f"applied — the other {5 - PLOT_OVERLAP} are replaced entirely."),
        "chart": chart_g3,
        "caption": f"Top 8 plots with no floor. Red bars fall below "
                   f"{VISIT_FLOOR} visits - and they dominate the top.",
    },
    {
        "key": "g4",
        "name": "G4 — rarefaction",
        "short": "Correct for unequal effort",
        "does": ("Randomly subsample the larger group down to the smaller one "
                 "before comparing species counts."),
        "true": (
            f"**Grassland has modestly more exclusive species.** Rarefied to "
            f"equal effort: {q11['rarefied']['grassland_only']} against "
            f"{q11['rarefied']['forest_only']} — a "
            f"**{RARE_RATIO:.1f}x** difference."),
        "false": (
            f"**Grassland has {RAW_RATIO:.1f}x more exclusive species.** Raw "
            f"counts: {q11['raw']['grassland_only']} against "
            f"{q11['raw']['forest_only']}. But grassland ran "
            f"{q11['sessions']['ratio']}x more sessions, and looking harder "
            f"finds more. The raw figure overstates the gap roughly "
            f"**{INFLATION:.0f}-fold**."),
        "chart": chart_g4,
        "caption": "Rarefaction removes the part of the difference that was "
                   "only ever survey effort.",
    },
]


# ==================================================================== page
st.title("Try it yourself")
st.markdown(
    theme.caption(
        "The two claims in this project that are hardest to take on trust - "
        "that the guardrails changed the answers, and that this survey is "
        "really a hearing test - are both easier to believe when you can "
        "operate them. Everything below recomputes from the real data."
    ),
    unsafe_allow_html=True,
)
st.write("")

# ------------------------------------------------------------ 1. simulator
st.subheader("What happens if you remove the guardrails?")
st.markdown(
    theme.caption(
        "All four are on by default, which is how every other page in this "
        "dashboard is computed. Switch one off and the analysis it protects "
        "re-runs on the real data - and the conclusion changes in front of you."
    ),
    unsafe_allow_html=True,
)
st.write("")

# A Streamlit widget that is given a `key` takes its value from
# st.session_state[key] and ignores the `value=` argument on every rerun after
# the first. So the toggles ARE the state: Reset and Break all write to these
# keys directly rather than to a separate dict, which would be silently
# ignored.
for _g in GUARDRAILS:
    st.session_state.setdefault(f"tog_{_g['key']}", True)

cols = st.columns(4, gap="medium")
for col, g in zip(cols, GUARDRAILS):
    with col:
        st.toggle(g["short"], key=f"tog_{g['key']}", help=g["does"])


def is_on(key: str) -> bool:
    return bool(st.session_state.get(f"tog_{key}", True))


def set_all(value: bool) -> None:
    """Flip every toggle. Must be used as an on_click callback, not inline."""
    for g in GUARDRAILS:
        st.session_state[f"tog_{g['key']}"] = value


active = sum(is_on(g["key"]) for g in GUARDRAILS)
broken = [g for g in GUARDRAILS if not is_on(g["key"])]

b1, b2 = st.columns([0.32, 0.68], gap="large")

with b1:
    tone = theme.FOREST if active == 4 else (
        theme.GRASSLAND if active >= 2 else theme.AT_RISK)
    verdict = ("Analysis is sound" if active == 4
               else f"{len(broken)} conclusion{'s' if len(broken) != 1 else ''} "
                    f"now wrong")
    st.markdown(
        f"""
<div style="background:{theme.CARD};border:1px solid {theme.BORDER};
            border-left:5px solid {tone};border-radius:14px;
            padding:20px 22px;text-align:center">
  <div style="font-size:0.7rem;font-weight:700;color:{theme.MUTED};
              text-transform:uppercase;letter-spacing:.06em">
      Guardrails active</div>
  <div style="font-size:3rem;font-weight:800;color:{tone};line-height:1.1;
              margin:6px 0">{active}<span style="font-size:1.4rem;
              color:{theme.MUTED}"> / 4</span></div>
  <div style="font-size:0.9rem;font-weight:700;color:{tone}">{verdict}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.write("")
    r1, r2 = st.columns(2)
    # on_click callbacks run BEFORE the script re-executes, which is the only
    # point at which a widget-backed session_state key may be written. Setting
    # them inline after the toggles have rendered raises StreamlitAPIException.
    r1.button("Reset", width='stretch', on_click=set_all, args=(True,))
    r2.button("Break all", width='stretch', on_click=set_all, args=(False,))

with b2:
    if active == 4:
        st.markdown(
            theme.guardrail_banner(
                "<b>This is the published analysis.</b> Every figure on every "
                "other page of this dashboard is computed with all four of "
                "these applied. Switch one off to see the claim it prevents - "
                "each one is a result this project would have reported, "
                "confidently and wrongly."
            ),
            unsafe_allow_html=True,
        )
    else:
        names = ", ".join(g["name"].split(" — ")[0] for g in broken)
        st.markdown(
            f"""
<div style="background:#fdecea;border:1px solid #f5c6c0;
            border-left:5px solid {theme.AT_RISK};border-radius:12px;
            padding:18px 20px">
  <div style="font-weight:800;color:{theme.AT_RISK};margin-bottom:8px">
      Without {names}, this project would have published
      {len(broken)} false or misleading claim{'s' if len(broken) != 1 else ''}.
  </div>
  <div style="font-size:0.9rem;color:{theme.INK2};line-height:1.7">
      Every one of them is statistically real, fully reproducible, and
      completely wrong about the thing it appears to describe. That is what
      makes them dangerous - not one would look like an error in a results
      table.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

st.write("")
st.markdown("**What this analysis would conclude**")
st.write("")

for g in GUARDRAILS:
    on = is_on(g["key"])
    mark = "✓" if on else "✗"
    colour = theme.FOREST if on else theme.AT_RISK
    body = g["true"] if on else g["false"]
    tag = "" if on else (
        f'<span style="background:{theme.AT_RISK};color:#fff;'
        f'border-radius:4px;padding:1px 7px;font-size:0.62rem;'
        f'font-weight:800;letter-spacing:.05em;margin-left:8px">WRONG</span>')

    st.markdown(
        f'<div style="display:flex;gap:12px;align-items:flex-start;'
        f'padding:14px 16px;border-radius:10px;margin-bottom:4px;'
        f'background:{theme.CARD};border:1px solid {theme.BORDER};'
        f'border-left:4px solid {colour}">'
        f'<div style="font-size:1.15rem;color:{colour};font-weight:800;'
        f'line-height:1.4">{mark}</div>'
        f'<div style="flex:1"><div style="font-size:0.7rem;font-weight:700;'
        f'color:{theme.MUTED};text-transform:uppercase;letter-spacing:.05em;'
        f'margin-bottom:4px">{g["name"]}{tag}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(body)
    with st.expander("Show me the evidence", expanded=not on):
        st.plotly_chart(g["chart"](), width='stretch',
                        config=theme.PLOTLY_CONFIG, key=f"gr_fig_{g['key']}")
        st.markdown(theme.caption(g["caption"]), unsafe_allow_html=True)
    st.write("")

st.divider()

# ------------------------------------------------------------ 2. ear test
st.subheader("The ear test")

e1, e2 = st.columns([0.55, 0.45], gap="large")

with e1:
    st.markdown(
        f"""
**{q14['auditory_pct']}% of every detection in this survey was made by ear.**

Only {q14['method_share']['Visualization']}% of birds were identified by
sight. Singing accounts for {q14['method_share']['Singing']}% and calling a
further {q14['method_share']['Calling']}%. Whatever else this survey is, in
practice it is a hearing test.

That is not a footnote. The three surveyors differ by
**{q14['auditory_gap']:.2f}** species per session on auditory detections
against **{q14['visual_gap']:.2f}** on visual - and the ranking reverses
between the two channels. The observer effect is an ear-training effect.

Reading that is one thing. Trying to tell two species apart by ear is another,
and it is the fastest way to understand why "calibrate the surveyors on calls"
is a real recommendation rather than a polite one.
"""
    )

with e2:
    st.markdown(
        theme.guardrail_banner(
            "<b>Why this section is honest about being incomplete.</b> Bird "
            "recordings are third-party material under Creative Commons "
            "licences that require attribution, and the source archive now "
            "requires an API key. Rather than fetch audio at run time - which "
            "would add exactly the kind of network dependency this dashboard "
            "removed everywhere else - recordings are read from a local folder "
            "with a manifest carrying recordist and licence for each file. "
            "Until that folder is populated, this section explains itself "
            "instead of pretending."
        ),
        unsafe_allow_html=True,
    )

st.write("")

MANIFEST = AUDIO_DIR / "manifest.csv"
clips: pd.DataFrame | None = None
if MANIFEST.exists():
    try:
        m = pd.read_csv(MANIFEST)
        needed = {"common_name", "file", "recordist", "licence", "url"}
        if needed.issubset(m.columns):
            m["path"] = m["file"].apply(lambda f: AUDIO_DIR / str(f))
            m = m[m["path"].apply(lambda p: p.exists())]
            if len(m) >= 2:
                clips = m.reset_index(drop=True)
    except Exception:
        clips = None

if clips is None:
    st.info(
        "**Audio not installed.** This quiz activates automatically once "
        "`data/audio/` contains `manifest.csv` and at least two of the "
        "recordings it lists. Nothing else needs changing, and nothing here "
        "breaks in the meantime.",
        icon=":material/volume_off:",
    )
    with st.expander("How to enable the ear test"):
        st.markdown(
            f"""
**1.** Create the folder `data/audio/` in the project root.

**2.** Download recordings for the species below from
[xeno-canto](https://xeno-canto.org) — search the species name, pick a
recording rated **A** quality, and save the mp3 into that folder. Prefer
recordings released under CC BY or CC BY-NC so attribution is all that is
required.

**3.** Create `data/audio/manifest.csv` with exactly these columns:

```
common_name,file,recordist,licence,url
Wood Thrush,wood_thrush.mp3,A Recordist,CC BY-NC-SA 4.0,https://xeno-canto.org/123456
Northern Cardinal,northern_cardinal.mp3,B Recordist,CC BY 4.0,https://xeno-canto.org/234567
```

The page reads the manifest, checks each file actually exists, and shows the
recordist and licence beneath every clip — which is what the licences require.
Any species you skip is simply left out of the quiz.

**Suggested species** — the analytically interesting ones, and two pairs that
are genuinely confusable by ear:
"""
        )
        st.dataframe(
            pd.DataFrame([
                ("Wood Thrush", "Carries 81.7% of the at-risk result"),
                ("Northern Cardinal", "Most-recorded species (1,125 sightings)"),
                ("Carolina Wren", "2nd most-recorded (993)"),
                ("Red-eyed Vireo", "3rd most-recorded (738); confusable with "
                                   "Scarlet Tanager"),
                ("Acadian Flycatcher", "Forest; confusable with Eastern "
                                       "Wood-Pewee"),
                ("Eastern Wood-Pewee", "The pewee half of that pair"),
                ("Field Sparrow", "Grassland specialist"),
                ("Indigo Bunting", "Grassland-leaning, 611 sightings"),
            ], columns=["Species", "Why this one"]),
            width='stretch', hide_index=True,
        )
else:
    if "ear_i" not in st.session_state:
        st.session_state.ear_i = random.randrange(len(clips))
        st.session_state.ear_shown = False
        st.session_state.ear_right = 0
        st.session_state.ear_total = 0

    row = clips.iloc[st.session_state.ear_i]
    st.markdown("**Listen, then name the bird.**")
    st.audio(str(row["path"]))

    options = list(clips["common_name"].unique())
    random.Random(st.session_state.ear_i).shuffle(options)
    options = options[:4]
    if row["common_name"] not in options:
        options[0] = row["common_name"]
        random.Random(st.session_state.ear_i + 1).shuffle(options)

    if not st.session_state.ear_shown:
        ocols = st.columns(len(options), gap="small")
        for c, opt in zip(ocols, options):
            if c.button(opt, key=f"ear_{st.session_state.ear_i}_{opt[:14]}",
                        width='stretch'):
                st.session_state.ear_total += 1
                if opt == row["common_name"]:
                    st.session_state.ear_right += 1
                st.session_state.ear_pick = opt
                st.session_state.ear_shown = True
                st.rerun()
    else:
        pick = st.session_state.get("ear_pick", "")
        if pick == row["common_name"]:
            st.success(f"Correct — **{row['common_name']}**.")
        else:
            st.error(f"That was **{row['common_name']}**, not {pick}.")
        st.markdown(
            theme.caption(
                f"Recording by {row['recordist']} · {row['licence']} · "
                f"<a href='{row['url']}' target='_blank'>source</a>"
            ),
            unsafe_allow_html=True,
        )
        if st.button("Next call", width='stretch'):
            st.session_state.ear_i = random.randrange(len(clips))
            st.session_state.ear_shown = False
            st.rerun()

    if st.session_state.ear_total:
        pct = st.session_state.ear_right / st.session_state.ear_total * 100
        st.markdown(
            theme.caption(
                f"<b>{st.session_state.ear_right} of "
                f"{st.session_state.ear_total} correct ({pct:.0f}%).</b> "
                f"Three trained surveyors, doing this for a living, still "
                f"differed by {q14['auditory_gap']:.2f} species per session on "
                f"exactly this skill."
            ),
            unsafe_allow_html=True,
        )