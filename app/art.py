"""
The illustration layer - hand-drawn inline SVG, no image files.

Everything here is drawn in code rather than loaded from a PNG. That is not
showing off: it means the whole illustration set is a few kilobytes, scales to
any screen without blurring, recolours from theme.py, and needs no image
hosting when the app deploys.

The sidebar scene is built from three depth layers - far pines, near pines and
a foreground stag - at different opacities. That is what makes it read as a
landscape rather than a row of triangles.
"""
from __future__ import annotations

import theme


def logo(size: int = 30, colour: str = "#ffffff") -> str:
    """A stylised feather-and-tree mark for the sidebar header."""
    return f'''<svg viewBox="0 0 48 48" width="{size}" height="{size}">
<path d="M24 6c-1.6 3.4-4.6 5.4-8.4 5.9 1.1 3.2 3.6 5.2 7 5.6-2.4 3.1-6 4.3-9.9
3.6 1.9 3.6 5.2 5.4 9.3 5.1-1.1 4.6-4.4 7.6-9.2 8.6 3.6 2.4 7.9 2.4 11.2.1V44h2
v-9.1c3.3 2.3 7.6 2.3 11.2-.1-4.8-1-8.1-4-9.2-8.6 4.1.3 7.4-1.5 9.3-5.1-3.9.7-7.5
-.5-9.9-3.6 3.4-.4 5.9-2.4 7-5.6C28.6 11.4 25.6 9.4 24 6z" fill="{colour}"/>
</svg>'''


def _pine(x: float, base: float, height: float, width: float,
          fill: str, opacity: float) -> str:
    """One conifer, drawn as four stacked tiers plus a trunk."""
    out = []
    for i in range(4):
        t = i / 4.0
        y_top = base - height * (1 - t)
        half = width * (0.42 + 0.58 * t)
        y_bottom = base - height * (0.74 - t * 0.74)
        out.append(
            f'<path d="M{x},{y_top:.1f} L{x - half:.1f},{y_bottom:.1f} '
            f'L{x + half:.1f},{y_bottom:.1f} Z" fill="{fill}" opacity="{opacity}"/>'
        )
    out.append(
        f'<rect x="{x - 1.6}" y="{base - height * 0.09:.1f}" width="3.2" '
        f'height="{height * 0.11:.1f}" fill="{fill}" opacity="{opacity}"/>'
    )
    return "".join(out)


def _bird(x: float, y: float, size: float, opacity: float) -> str:
    """A bird in flight - two joined curves, the way anyone sketches one."""
    return (
        f'<path d="M{x - size},{y} q{size * 0.55},{-size * 0.75} {size},{-size * 0.08} '
        f'q{size * 0.45},{-size * 0.67} {size},{size * 0.08}" fill="none" '
        f'stroke="#dff0e2" stroke-width="{max(1.1, size * 0.20):.1f}" '
        f'stroke-linecap="round" opacity="{opacity}"/>'
    )


def scene(width: int = 260, height: int = 185) -> str:
    """
    The sidebar foot: mist, two ranks of pines, a stag, and birds overhead.

    The stag is assembled from simple readable parts - four legs, a body, a
    neck, a head and stroked antlers - rather than one clever path. Simple
    parts stay recognisable at small sizes; a single complex outline turns to
    mush.
    """
    dark = "#0a1710"
    s = [f'<svg viewBox="0 0 212 {height}" width="100%" style="display:block">']

    # Mist: a vertical fade that seats the scene into the sidebar gradient.
    s.append(
        '<defs><linearGradient id="birdmist" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1e3a28" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#0a1a10" stop-opacity=".9"/>'
        '</linearGradient></defs>'
        f'<rect width="212" height="{height}" fill="url(#birdmist)"/>'
    )

    for bx, by, bs, bo in [(44, 26, 7, .75), (66, 15, 5.5, .55), (88, 32, 4.5, .45),
                           (150, 22, 6, .6), (172, 38, 4, .38)]:
        s.append(_bird(bx, by, bs, bo))

    # Far rank - lighter and shorter, so it reads as distance.
    for x, h, w in [(16, 52, 13), (40, 42, 10), (62, 58, 14), (90, 46, 11),
                    (118, 54, 13), (146, 44, 11), (174, 56, 14), (198, 46, 11)]:
        s.append(_pine(x, 150, h, w, "#23412d", .85))

    # Near rank - darker, taller, overlapping the far one.
    for x, h, w in [(6, 74, 17), (30, 62, 15), (56, 82, 19), (86, 66, 16),
                    (112, 78, 18), (140, 64, 15), (166, 80, 18), (196, 68, 16)]:
        s.append(_pine(x, 162, h, w, "#122619", 1))

    s.append(f'''<g>
<rect x="82" y="145" width="3.6" height="17" rx="1.6" fill="{dark}"/>
<rect x="90" y="145" width="3.6" height="17" rx="1.6" fill="{dark}"/>
<rect x="104" y="145" width="3.6" height="17" rx="1.6" fill="{dark}"/>
<rect x="112" y="145" width="3.6" height="17" rx="1.6" fill="{dark}"/>
<path d="M80,146 q-2,-16 10,-18 l20,0 q10,1 10,9 0,9 -10,9 z" fill="{dark}"/>
<path d="M78,138 q-5,-3 -6,-10 q4,4 8,5 z" fill="{dark}"/>
<path d="M112,134 q1,-10 7,-14 l6,-4 q4,-2 5,2 q1,4 -3,6 l-5,3 q-3,3 -3,9 z" fill="{dark}"/>
<path d="M124,118 q5,-2 8,1 q3,3 -1,5 q-4,2 -8,-1 z" fill="{dark}"/>
<path d="M126,116 l-2,-11 M124,105 l-5,-5 M124,109 l6,-6 M130,114 l3,-12
         M133,102 l6,-4 M133,106 l-5,-4"
      stroke="{dark}" stroke-width="2.4" stroke-linecap="round" fill="none"/>
</g>''')

    s.append(f'<rect y="{height - 14}" width="212" height="14" fill="#0a120d"/>')
    s.append("</svg>")
    return "".join(s)


# 24x24 icon paths, drawn on the same grid so they sit together consistently.
ICONS = {
    "overview": "M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z",
    "habitat": "M12 2l4 7h-3v5h-2V9H8zM4 16h16v6H4z",
    "species": "M6 20c0-6 4-10 10-10 2 0 4 .6 5 1.5C19 16 15 20 9 20zM4 12a3 3 0 1 1 6 0 3 3 0 0 1-6 0z",
    "where": "M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z",
    "time": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 10.6V6h-2v7.4l5.2 3.1 1-1.7z",
    "weather": "M6 18a4 4 0 0 1 .6-8 6 6 0 0 1 11.3 2A3.5 3.5 0 0 1 18 18z",
    "quality": "M12 2l8 4v6c0 5-3.4 8.8-8 10-4.6-1.2-8-5-8-10V6zm-1 13l6-6-1.4-1.4L11 12.2 8.4 9.6 7 11z",
    "report": "M6 2h8l4 4v16H6zm7 1.5V7h3.5zM8 11h8v2H8zm0 4h8v2H8z",
    "conclusion": "M9 21h6v-1H9zm3-19a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z",
    "ai": "M12 2a2 2 0 0 1 2 2v1h3a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h3V4a2 2 0 0 1 2-2zM9 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z",
    "bird": "M6 20c0-6 4-10 10-10 2 0 4 .6 5 1.5C19 16 15 20 9 20zM4 12a3 3 0 1 1 6 0 3 3 0 0 1-6 0z",
    "grid": "M3 3h8v8H3zm10 0h8v8h-8zM3 13h8v8H3zm10 0h8v8h-8z",
    "alert": "M12 2l10 18H2zm-1 7v5h2V9zm0 7v2h2v-2z",
}


def icon(name: str, size: int = 18, colour: str = "currentColor") -> str:
    """One icon from the set. Unknown names fall back to the bird."""
    path = ICONS.get(name, ICONS["bird"])
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" '
            f'fill="{colour}"><path d="{path}"/></svg>')


def sidebar_header(title: str = "Bird Species<br/>Observation") -> str:
    """Logo and wordmark for the top of the sidebar."""
    return f'''<div style="display:flex;align-items:center;gap:12px;
                           margin:-16px 0 14px;padding:0 0 12px;
                           border-bottom:1px solid rgba(255,255,255,.11)">
  {logo(40)}
  <div style="font-size:1.56rem;font-weight:800;line-height:1.50;color:#fff;
              letter-spacing:-0.015em">
    {title}
  </div>
</div>'''


def sidebar_scene() -> str:
    """The illustration, wrapped so it sits flush at the sidebar foot."""
    return f'<div style="margin:18px -1.5rem -1rem">{scene()}</div>'