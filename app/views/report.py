"""
Report - the full written report, on screen and as downloadable documents.

The content is not defined here. It lives in src/report_content.py as a list of
typed blocks, and this module is one of three renderers for it - the other two
produce the PDF and the Word file. That separation is deliberate: an evaluator
who found the on-screen report and the PDF disagreeing would have no reason to
trust either, and writing the report three times guarantees exactly that.

Layout:
  1. title, scope and the download buttons
  2. a section jump-list
  3. the report itself, rendered block by block
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

import data_access as da
import theme

# src/ is already on the path via data_access, which imports analysis from it.
import report_content as rc  # noqa: E402

DOCS = da.ROOT / "docs"
LEDGER = DOCS / "findings-ledger.md"

VERDICT_COLOUR = {
    "finding": theme.FOREST,
    "narrowed": theme.GRASSLAND,
    "rejected": theme.AT_RISK,
    "descriptive": theme.MUTED,
    "method": theme.NAV_ACTIVE,
}


@st.cache_data(show_spinner="Assembling the report...")
def blocks():
    """The report content. Cached - it re-runs the whole analysis."""
    return rc.build_blocks()


@st.cache_data(show_spinner="Rendering the PDF...")
def pdf_bytes() -> bytes | None:
    """Render the PDF, or None if reportlab is unavailable in this install."""
    try:
        import make_report
        return make_report.build_pdf()
    except Exception:
        return None


@st.cache_data(show_spinner="Rendering the Word document...")
def docx_bytes() -> bytes | None:
    """Render the .docx, or None if python-docx is unavailable."""
    try:
        import make_report
        return make_report.build_docx()
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def ledger_markdown() -> str | None:
    """The findings ledger, if it has been generated or can be built."""
    if LEDGER.exists():
        try:
            return LEDGER.read_text(encoding="utf-8")
        except OSError:
            pass
    try:
        import make_ledger
        return make_ledger.build()
    except Exception:
        return None


BLOCKS, CTX = blocks()

# ------------------------------------------------------------------ 1. header
st.title("Report")
st.markdown(
    theme.caption(
        f"{len(CTX['rows']):,} sightings · {len(CTX['sessions']):,} survey "
        f"sessions · {CTX['rows']['Scientific_Name'].nunique()} species · "
        f"{CTX['r']['q12']['n_parks']} National Park Service units · 2018 "
        f"breeding season. The full report is reproduced below and is "
        f"available as a formatted document. Every figure is computed by the "
        f"analysis pipeline at build time - nothing is typed by hand, here or "
        f"in the documents."
    ),
    unsafe_allow_html=True,
)
# Streamlit's primary button is red by default, which reads as an error next
# to this theme. Scoped to this page so theme.py stays untouched.
st.markdown(
    f"""
<style>
  [data-testid="stBaseButton-primary"] {{
      background: {theme.FOREST} !important;
      border-color: {theme.FOREST} !important;
      color: #ffffff !important;
  }}
  [data-testid="stBaseButton-primary"]:hover {{
      background: {theme.SIDEBAR_BOTTOM} !important;
      border-color: {theme.SIDEBAR_BOTTOM} !important;
  }}
</style>
""",
    unsafe_allow_html=True,
)
st.write("")

d1, d2, d3 = st.columns(3, gap="medium")

with d1:
    pdf = pdf_bytes()
    if pdf:
        st.download_button(
            "Download report (PDF)", data=pdf,
            file_name="Bird_Species_Observation_Analysis_Report.pdf",
            mime="application/pdf", width='stretch', type="primary",
        )
    else:
        st.button("PDF unavailable", disabled=True, width='stretch',
                  help="reportlab is not installed. Add `reportlab` to "
                       "requirements.txt and reinstall.")

with d2:
    docx = docx_bytes()
    if docx:
        st.download_button(
            "Download report (Word)", data=docx,
            file_name="Bird_Species_Observation_Analysis_Report.docx",
            mime="application/vnd.openxmlformats-officedocument."
                 "wordprocessingml.document",
            width='stretch',
        )
    else:
        st.button("Word unavailable", disabled=True, width='stretch',
                  help="python-docx is not installed. Add `python-docx` to "
                       "requirements.txt and reinstall.")

with d3:
    ledger = ledger_markdown()
    if ledger:
        st.download_button(
            "Download findings ledger (.md)", data=ledger,
            file_name="bird-analysis-findings-ledger.md",
            mime="text/markdown", width='stretch',
        )
    else:
        st.button("Ledger unavailable", disabled=True, width='stretch',
                  help="Run `python src/make_ledger.py` to generate it.")

st.write("")
st.divider()

# ------------------------------------------------------------------ 2. jump list
parts = [b[1] for b in BLOCKS if b[0] == "h1"]
st.markdown(
    theme.caption(
        "<b>Contents.</b> " + " &nbsp;·&nbsp; ".join(parts)
    ),
    unsafe_allow_html=True,
)
st.write("")
st.divider()


# ------------------------------------------------------------------ 3. render
def render(block: tuple) -> None:
    kind = block[0]

    if kind == "pagebreak":
        return                      # a print concern only

    if kind == "h1":
        st.write("")
        st.markdown(
            f'<div style="border-top:2px solid {theme.FOREST};'
            f'padding-top:14px;margin-top:10px"></div>',
            unsafe_allow_html=True,
        )
        st.header(block[1])

    elif kind == "h2":
        st.subheader(block[1])

    elif kind == "h3":
        st.markdown(
            f'<div style="font-weight:800;color:{theme.INK2};'
            f'font-size:1rem;margin:10px 0 4px">{block[1]}</div>',
            unsafe_allow_html=True,
        )

    elif kind == "p":
        st.markdown(
            f'<div style="font-size:0.95rem;color:{theme.INK};'
            f'line-height:1.75;margin-bottom:10px">{block[1]}</div>',
            unsafe_allow_html=True,
        )

    elif kind == "bullets":
        items = "".join(
            f'<li style="margin-bottom:8px">{i}</li>' for i in block[1]
        )
        st.markdown(
            f'<ul style="font-size:0.95rem;color:{theme.INK};line-height:1.7;'
            f'padding-left:22px;margin-bottom:12px">{items}</ul>',
            unsafe_allow_html=True,
        )

    elif kind == "kv":
        rows_html = "".join(
            f'<tr>'
            f'<td style="padding:7px 12px 7px 0;border-bottom:1px solid '
            f'{theme.BORDER};font-weight:700;color:{theme.INK};'
            f'vertical-align:top;width:28%">{k}</td>'
            f'<td style="padding:7px 0;border-bottom:1px solid '
            f'{theme.BORDER};color:{theme.INK2};vertical-align:top">{v}</td>'
            f'</tr>' for k, v in block[1]
        )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;'
            f'font-size:0.9rem;line-height:1.6;margin-bottom:14px">'
            f'{rows_html}</table>',
            unsafe_allow_html=True,
        )

    elif kind == "table":
        df = block[1]
        show = df.reset_index() if (
            df.index.name or not isinstance(df.index, pd.RangeIndex)
        ) else df
        st.dataframe(show, width='stretch', hide_index=True)
        st.markdown(theme.caption(block[2]), unsafe_allow_html=True)
        st.write("")

    elif kind == "note":
        st.markdown(theme.guardrail_banner(block[1]), unsafe_allow_html=True)

    elif kind == "verdict":
        colour = VERDICT_COLOUR.get(block[1], theme.MUTED)
        label = rc.VERDICT_LABELS.get(block[1], block[1].upper())
        st.markdown(
            f'<div style="margin-bottom:14px">'
            f'<span style="background:{colour};color:#fff;border-radius:5px;'
            f'padding:3px 10px;font-size:0.7rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em">{label}</span>'
            f'<div style="border-left:3px solid {colour};padding:8px 0 8px 14px;'
            f'margin-top:8px;font-size:0.95rem;color:{theme.INK};'
            f'line-height:1.7">{block[2]}</div></div>',
            unsafe_allow_html=True,
        )


for _block in BLOCKS:
    render(_block)

st.write("")
st.divider()
st.markdown(
    theme.caption(
        "This report is generated from <code>src/report_content.py</code>. The "
        "PDF and Word documents above are rendered from the same source by "
        "<code>src/make_report.py</code>, so the printed and on-screen "
        "versions cannot disagree. Regenerate the documents from the project "
        "root with <code>python src/make_report.py</code>."
    ),
    unsafe_allow_html=True,
)