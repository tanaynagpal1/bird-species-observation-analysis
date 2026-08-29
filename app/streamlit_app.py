"""
Deployment smoke test.

Deliberately minimal. Its only job is to prove that the parts most likely to
break in the cloud actually work:

  - the app can find src/ and import our modules
  - the processed CSVs are committed and readable
  - pandas, numpy and streamlit all load on the deploy host
  - file paths resolve when the working directory is not what we expect

If this page renders the right numbers on Streamlit Cloud, every hard part of
deployment is already solved and what remains is only adding charts.
"""
import sys
from pathlib import Path

import streamlit as st

# The app lives in app/, our modules live in src/. This works both locally and
# on the deploy host, because it resolves relative to THIS file rather than to
# whatever directory the process happens to start in.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analysis  # noqa: E402

st.set_page_config(page_title="Bird Species Observation Analysis",
                   page_icon="🪶", layout="wide")

st.title("Deployment smoke test")
st.caption("Bird Species Observation Analysis — checking the pipeline loads before we build the dashboard.")


@st.cache_data
def get_tables():
    return analysis.load_tables()


try:
    t = get_tables()
except Exception as exc:
    st.error("Could not load the processed data files.")
    st.exception(exc)
    st.stop()

st.success("Data loaded successfully.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Observations", f"{len(t['rows']):,}")
c2.metric("Survey sessions", f"{len(t['sessions']):,}")
c3.metric("Species", f"{t['rows'].Scientific_Name.nunique()}")
c4.metric("Parks", f"{t['rows'].Admin_Unit_Code.nunique()}")

st.divider()
st.subheader("Headline figures, computed live")

q1 = analysis.q1_at_risk_by_habitat(t["sessions"])
q1b = analysis.q1b_at_risk_without_wood_thrush(t["rows"])
q2 = analysis.q2_richness_by_habitat(t["sessions"])
q4 = analysis.q4_specialists(t["species"])

left, right = st.columns(2)

with left:
    st.markdown("**At-risk species rate — the headline**")
    st.write(
        f"Forest **{q1['forest_pct']}%** vs Grassland **{q1['grassland_pct']}%** "
        f"= **{q1['ratio']}x** (p = {q1['p_value']:.2e})"
    )
    st.caption(
        f"Wood Thrush alone is {q1b['wood_thrush_share_pct']}% of all at-risk "
        f"sightings. Excluding it the ratio falls to "
        f"{q1b['without_wood_thrush']['ratio']}x."
    )
    st.dataframe(q1["by_park"], use_container_width=True)

with right:
    st.markdown("**Species richness — the null result**")
    st.write(
        f"Pooled across 11 parks: {q2['pooled']['forest']} vs "
        f"{q2['pooled']['grassland']} (p = {q2['pooled']['p_value']:.4f}) — "
        f"significant, but confounded."
    )
    st.write(
        f"Within the 4 shared parks: {q2['within_shared']['forest']} vs "
        f"{q2['within_shared']['grassland']} (p = "
        f"{q2['within_shared']['p_value']:.3f}) — no difference."
    )
    st.dataframe(q2["by_park"], use_container_width=True)

st.divider()
st.subheader("Habitat specialists")
st.write(
    f"**{q4['n_grassland']}** grassland specialists · "
    f"**{q4['n_forest']}** forest specialists · "
    f"**{q4['n_generalist']}** generalists"
)

st.divider()
st.caption(
    f"Python {sys.version.split()[0]} · "
    f"pandas {__import__('pandas').__version__} · "
    f"streamlit {st.__version__} · running from {ROOT.name}"
)