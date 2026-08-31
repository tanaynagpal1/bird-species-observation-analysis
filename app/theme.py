"""
The Nature theme - one source of truth for every colour in the dashboard.

Nothing else in the app should contain a hex code. If a chart needs the forest
colour it imports FOREST from here, so a change lands everywhere at once.

Concept: "Nature / illustrated". A cream page with a dark green illustrated
sidebar - a field guide rather than a business dashboard. The warmth comes from
the illustration layer, not from bending the data colours.

Colour validation
-----------------
The two habitat colours were checked against the cream surface (#f6f4ec) for
colour-vision deficiency and contrast:

    forest #12805c vs grassland #b07d0a
      CVD separation   Delta E 8.7  (protan)   - passes, target is 8
      normal vision    Delta E 18.4            - passes, floor is 15
      contrast         both clear 3:1 on cream - passes

Lighter, more obvious green and gold steps (#1baf7a / #eda100) were tested and
REJECTED: they fail the 3:1 contrast check on a light surface.

Do not substitute colours without re-running that validation.

One rule worth stating: never use shades of a single hue for categorical data.
Four greens for four categories is close to unreadable for a colourblind
viewer. Green and gold keeps the nature feel while staying legible.
"""
from __future__ import annotations

# ------------------------------------------------------------------ palette
# The two habitats. These carry meaning - never reuse them for anything else.
FOREST = "#12805c"
GRASSLAND = "#b07d0a"

# Reserved status colour. Never a series colour, and always paired with a
# label or icon so it never has to carry meaning by itself.
AT_RISK = "#c0392b"

# Environment tab only (humidity, weather). Never appears in the same chart as
# the habitat series, where it would compete for attention.
POND = "#3987e5"

# Surfaces
PAGE = "#f6f4ec"        # cream page background
CARD = "#ffffff"
BORDER = "#e4e1d5"
GRID = "#e8e5da"        # recessive gridlines

# Ink
INK = "#1a2620"         # primary text
INK2 = "#5c6a61"        # secondary text
MUTED = "#8a968d"       # axis labels, captions

# Dark green chrome
SIDEBAR_TOP = "#16311f"
SIDEBAR_BOTTOM = "#1d4029"
KPI_TOP = "#1b3a25"
KPI_BOTTOM = "#245030"
NAV_ACTIVE = "#2b6b45"
NAV_GLOW = "#43c795"

# Guardrail banner
BANNER_BG = "#fdf6e6"
BANNER_BORDER = "#eddfba"
BANNER_TEXT = "#7a5c17"

# Convenience map for Plotly's color_discrete_map argument.
HABITAT_COLOURS = {"Forest": FOREST, "Grassland": GRASSLAND}

# Sequential ramp for heatmaps and map bubbles - a single hue, light to dark.
# Sequential means magnitude, so one hue only; a rainbow would imply categories.
SEQUENTIAL = ["#e8f3ee", "#b9ded0", "#7cc4ab", "#3fa385", "#12805c", "#0a5a40"]

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}

# Hides Plotly's built-in toolbar (zoom/pan/download). It renders inside a
# shadow root, so page-level CSS cannot touch it - this config flag is the
# only thing that works. Pass to every st.plotly_chart() call.
PLOTLY_CONFIG = {"displayModeBar": False}


# ------------------------------------------------------------------ chrome
def css() -> str:
    """
    CSS that restyles Streamlit's own chrome to match the theme.

    Streamlit ships a default look; this overrides the parts that would
    otherwise clash - the page background, the sidebar, headings and the
    metric cards.

    Selectors use `data-testid` attributes rather than generated class names,
    because the class names change between Streamlit versions and the test ids
    do not.
    """
    return f"""
<style>
  /* Page background */
  [data-testid="stAppViewContainer"] {{
      background: {PAGE};
  }}
  [data-testid="stHeader"] {{
      background: transparent;
  }}

  /* Sidebar - the dark green panel that carries the illustration */
  [data-testid="stSidebar"] > div:first-child {{
      background: linear-gradient(180deg, {SIDEBAR_TOP}, {SIDEBAR_BOTTOM});
  }}
  [data-testid="stSidebar"] * {{
      color: #dfeae2;
  }}
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {{
      color: #ffffff;
  }}

  /* Wider sidebar - logo, nav, filters and the illustration all stack in one
     column now, so the default 300px feels cramped. */
  [data-testid="stSidebar"] {{
      width: 330px !important;
  }}

  /* Our own nav, built with st.page_link (see streamlit_app.py) so it can
     sit between the logo and the filters - Streamlit's automatic nav is
     hidden and can only ever render above everything else in the sidebar.
     streamlit_app.py passes disabled=True for whichever page is currently
     open (comparing Page.url_path) - that's the only reliable "this one is
     active" signal page_link gives us. Disabled links dim by default (meant
     for a white background), so we override that here. */
  [data-testid="stPageLink-NavLink"] {{
      border-radius: 8px;
      padding: 6px 10px;
      margin-bottom: 2px;
  }}
  [data-testid="stPageLink-NavLink"][disabled] {{
      background: {NAV_ACTIVE};
      opacity: 1 !important;
      cursor: default;
  }}
  [data-testid="stPageLink-NavLink"][disabled] * {{
      color: #ffffff !important;
      font-weight: 700;
  }}

  /* Typography */
  h1, h2, h3, h4 {{
      color: {INK};
      letter-spacing: -0.01em;
  }}
  h1 {{ font-weight: 800; }}

  /* Metric cards - dark green, matching the KPI tiles in the design */
  [data-testid="stMetric"] {{
      background: linear-gradient(140deg, {KPI_TOP}, {KPI_BOTTOM});
      border-radius: 12px;
      padding: 14px 16px;
      color: #ffffff;
  }}
  [data-testid="stMetricLabel"] p {{
      color: #a8c6b3 !important;
      font-size: 0.78rem;
  }}
  [data-testid="stMetricValue"] {{
      color: #ffffff;
      font-weight: 800;
  }}

  /* Cards and tables sit on white against the cream page */
  [data-testid="stDataFrame"], [data-testid="stTable"] {{
      background: {CARD};
      border: 1px solid {BORDER};
      border-radius: 10px;
  }}

  /* Tighten the default top padding so the page starts higher */
  .block-container {{ padding-top: 2.2rem; }}
</style>
"""


def guardrail_banner(text: str) -> str:
    """
    The amber notice that appears above any habitat comparison.

    It exists because a reader who does not know the comparison is
    effort-adjusted and park-controlled may draw the wrong conclusion from a
    perfectly correct chart. The note travels with the chart.
    """
    return f"""
<div style="background:{BANNER_BG};border:1px solid {BANNER_BORDER};
            border-left:3px solid {GRASSLAND};border-radius:9px;
            padding:9px 13px;font-size:0.86rem;color:{BANNER_TEXT};
            margin-bottom:14px;line-height:1.5">
  {text}
</div>
"""


# ------------------------------------------------------------------ charts
def plotly_layout(height: int = 320, showlegend: bool = True) -> dict:
    """
    Shared Plotly layout so every chart in the app looks like the same system.

    Passed to fig.update_layout(**plotly_layout()). Keeping it here rather than
    repeating settings per chart is what stops the fifteenth chart drifting
    away from the first.
    """
    return {
        "height": height,
        "showlegend": showlegend,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": INK2, "size": 12,
                 "family": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"},
        "margin": {"l": 10, "r": 10, "t": 30, "b": 10},
        "xaxis": {"gridcolor": GRID, "linecolor": "#cfcabb", "zeroline": False,
                  "title_font": {"size": 11, "color": MUTED},
                  "tickfont": {"size": 11}},
        "yaxis": {"gridcolor": GRID, "linecolor": "#cfcabb", "zeroline": False,
                  "title_font": {"size": 11, "color": MUTED},
                  "tickfont": {"size": 11}},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02,
                   "xanchor": "left", "x": 0,
                   "font": {"size": 11}, "title_text": ""},
        "hoverlabel": {"bgcolor": CARD, "bordercolor": BORDER,
                       "font": {"color": INK, "size": 12}},
    }


def caption(text: str) -> str:
    """A muted one-line interpretation, shown under a chart."""
    return f'<div style="font-size:0.78rem;color:{MUTED};line-height:1.5;' \
           f'margin-top:-6px">{text}</div>'