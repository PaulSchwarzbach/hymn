"""Generate the HYMN logo as scalable SVG files.

Concept "Konvergenz": one anchor per HYMN system sits on a pentagon and emits
concentric range arcs towards the centre, where an open ring marks the
position.

  - Anchors use the technology symbols and colours of the landing-page map:
    GNSS filled circle (top), BLE diamond, 5G NR hexagon, WiFi FTM rounded
    square, UWB triangle (clockwise). 5G NR is TUD CD Violett1 so it no longer
    shares the GNSS grey.
  - The pentagon is turned 14 deg clockwise. Upright, the star reads as a
    figure (head, arms, legs). It is mirror-symmetric again at 18 deg, so
    12-16 deg breaks the figure without laying it on its side. Glyphs stay
    upright like map symbols.
  - The open ring in the centre is the only open shape. The landing page marks
    total-station ground truth with the same ring.
  - Wordmark "HYMN" in Source Serif 4 Bold, expansion in Source Serif 4
    Semibold, both converted to outlines with fontTools (fonts located via
    MiKTeX kpsewhich), so the files do not depend on installed fonts.

Outputs in logo/:
  hymn-mark[-dark|-white].svg           mark on a 100 x 100 square
  hymn-mark-inline.svg                  mark coloured by the landing-page CSS tokens
                                        (--ink, --uwb, --ble, --wifi, --nr5g, --gnss),
                                        an HTML snippet for the topbar, not standalone
  hymn-icon.svg                         favicon: simplified mark on a dark tile
  hymn-icon-full.svg                    the same tile without corner radius
  apple-touch-icon.png                  hymn-icon-full.svg at 180 px
  hymn-logo[-dark|-white].svg           mark + wordmark + expansion, cropped to ink
  hymn-logo-compact[-dark|-white].svg   mark + wordmark, cropped to ink
  pdf/<name>.pdf                        every mark and lockup above as PDF (Beamer, print)

  -dark is for dark backgrounds, -white is monochrome white (e.g. Beamer title
  slide on TUD Tuerkis).

Usage:
    python make_logo.py          # write all outputs, check clearances
    python make_logo.py --png    # also write control renderings to logo/png/
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "logo"

# Technology colours and ink from assets/css/style.css of the landing page.
# 5G NR: TUD CD Violett1 (115,105,190), on dark ground mixed 30 % towards
# Violett2 (200,200,255).
PALETTES = {
    "light": dict(ink="#0b0b0b", ink2="#52514e", uwb="#2a78d6", ble="#eb6834",
                  wifi="#1baf7a", nr="#7369be", gnss="#52514e"),
    "dark": dict(ink="#ffffff", ink2="#c3c2b7", uwb="#3987e5", ble="#d95926",
                 wifi="#199e70", nr="#8c86d2", gnss="#c3c2b7"),
    "white": dict(ink="#ffffff", ink2="#ffffff", uwb="#ffffff", ble="#ffffff",
                  wifi="#ffffff", nr="#ffffff", gnss="#ffffff"),
    # favicon tile: brightest variant of each colour on near-black
    "tile": dict(ink="#fcfcfb", ink2="#c3c2b7", uwb="#3987e5", ble="#eb6834",
                 wifi="#1baf7a", nr="#8c86d2", gnss="#c3c2b7"),
    # inline mark: the page's tokens resolve to the light or dark values above
    "css": dict(ink="var(--ink)", ink2="var(--ink-2)", uwb="var(--uwb)", ble="var(--ble)",
                wifi="var(--wifi)", nr="var(--nr5g)", gnss="var(--gnss)"),
}
TILE_BG = "#0b0b0b"

WORDMARK_FONT = "SourceSerif4-Bold.otf"
TAGLINE_FONT = "SourceSerif4-Semibold.otf"
TAGLINE = "Hybrid Multi-technology Navigation"
TITLE = "HYMN, Hybrid Multi-technology Navigation"


def n(v: float) -> str:
    """Compact number formatting for SVG coordinates."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---------------------------------------------------------------- glyphs ---

def triangle(cx, cy, s, fill):
    """UWB: upward triangle, s = height."""
    hb = s * 0.6
    return (f'<polygon points="{n(cx)},{n(cy - s / 2)} {n(cx + hb)},{n(cy + s / 2)} '
            f'{n(cx - hb)},{n(cy + s / 2)}" fill="{fill}"/>')


def diamond(cx, cy, s, fill):
    """BLE: square on its tip, s = diagonal."""
    h = s / 2
    return (f'<polygon points="{n(cx)},{n(cy - h)} {n(cx + h)},{n(cy)} {n(cx)},{n(cy + h)} '
            f'{n(cx - h)},{n(cy)}" fill="{fill}"/>')


def square(cx, cy, s, fill):
    """WiFi FTM: rounded square, s = side."""
    return (f'<rect x="{n(cx - s / 2)}" y="{n(cy - s / 2)}" width="{n(s)}" height="{n(s)}" '
            f'rx="{n(s * 0.16)}" fill="{fill}"/>')


def hexagon(cx, cy, s, fill):
    """5G NR: flat-topped hexagon, s = width."""
    r = s / 2
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
           for a in range(0, 360, 60)]
    return f'<polygon points="{" ".join(f"{n(x)},{n(y)}" for x, y in pts)}" fill="{fill}"/>'


def dot(cx, cy, r, fill):
    return f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"/>'


def disc(cx, cy, s, fill):
    """GNSS: filled circle, s = diameter."""
    return dot(cx, cy, s / 2, fill)


def ring(cx, cy, r_out, r_in, fill):
    """Open ring as one even-odd path, so it stays transparent inside."""
    def circ(r, sweep):
        return (f"M{n(cx - r)},{n(cy)}a{n(r)},{n(r)} 0 1,{sweep} {n(2 * r)},0"
                f"a{n(r)},{n(r)} 0 1,{sweep} {n(-2 * r)},0Z")
    return f'<path d="{circ(r_out, 0)}{circ(r_in, 1)}" fill="{fill}" fill-rule="evenodd"/>'


def rect(x, y, w, h, fill, rx=0.0):
    rx_attr = f' rx="{n(rx)}"' if rx else ""
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"{rx_attr} fill="{fill}"/>'


def arc(cx, cy, r, a0, a1, width, stroke):
    """Circular arc from angle a0 to a1 (degrees, SVG orientation), round caps."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    return (f'<path d="M{n(x0)},{n(y0)}A{n(r)},{n(r)} 0 {large},1 {n(x1)},{n(y1)}" fill="none" '
            f'stroke="{stroke}" stroke-width="{n(width)}" stroke-linecap="round"/>')


# ------------------------------------------------------------------ mark ---

# (angle before rotation in screen degrees, palette key, glyph, glyph size)
ANCHORS = [(-90, "gnss", disc, 12.5), (-18, "ble", diamond, 15), (54, "nr", hexagon, 14),
           (126, "wifi", square, 11.5), (198, "uwb", triangle, 13)]
# full mark: 100 x 100 grid, re-centred on the glyph bounding box after rotation
MARK = dict(R=42, rot=14, radii=[12.9, 19.1, 25.3], spans=[36, 30, 21], width=3.45,
            ring=(8, 4.2))
# favicon: one thick arc per anchor, no glyphs, fixed centre
ICON = dict(R=40, rot=14, cy=52, radii=[16], spans=[34], width=9, ring=(10.4, 5.46))
MIN_GAP = 3.0  # required clearance between arcs of different anchors and to the ring


def glyph_extent(key, s):
    """Half width and half height of an anchor glyph of size s."""
    return {"uwb": (0.6 * s, 0.5 * s), "nr": (0.5 * s, 0.433 * s)}.get(key, (0.5 * s, 0.5 * s))


def geometry(icon=False):
    """Anchor positions and headings, pentagon centre, and glyph bounding box."""
    g = ICON if icon else MARK
    raw = []
    for ang, key, glyph, s in ANCHORS:
        a = math.radians(ang + g["rot"])
        raw.append((g["R"] * math.cos(a), g["R"] * math.sin(a), ang + g["rot"] + 180, key, glyph, s))
    ext = [glyph_extent(key, s) for *_, key, _, s in raw]
    box = (min(x - e[0] for (x, *_), e in zip(raw, ext)), min(y - e[1] for (_, y, *_), e in zip(raw, ext)),
           max(x + e[0] for (x, *_), e in zip(raw, ext)), max(y + e[1] for (_, y, *_), e in zip(raw, ext)))
    if icon:
        cx, cy = 50, g["cy"]
    else:
        cx, cy = 50 - (box[0] + box[2]) / 2, 50 - (box[1] + box[3]) / 2
    pts = [(x + cx, y + cy, h, key, glyph, s) for x, y, h, key, glyph, s in raw]
    box = (box[0] + cx, box[1] + cy, box[2] + cx, box[3] + cy)
    return g, pts, (cx, cy), box


def mark(p, icon=False, radius=22.0):
    """Inner SVG markup of the mark (or the favicon, tile corner `radius`) on a 100 x 100 grid."""
    g, pts, (cx, cy), _ = geometry(icon)
    out = [rect(0, 0, 100, 100, TILE_BG, radius)] if icon else []
    for x, y, heading, key, glyph, s in pts:
        for r, half in zip(g["radii"], g["spans"]):
            out.append(arc(x, y, r, heading - half, heading + half, g["width"], p[key]))
        if not icon:
            out.append(glyph(x, y, s, p[key]))
    out.append(ring(cx, cy, *g["ring"], p["ink"]))
    return "".join(out)


def check_clearances() -> None:
    """Sample the arcs and assert the minimum gaps (arc to arc, arc to centre ring)."""
    for icon in (False, True):
        g, pts, (cx, cy), _ = geometry(icon)
        w = g["width"]
        arcs = []
        for x, y, h, key, *_ in pts:
            for r, half in zip(g["radii"], g["spans"]):
                a0, a1 = math.radians(h - half), math.radians(h + half)
                arcs.append((key, [(x + r * math.cos(a0 + (a1 - a0) * i / 80),
                                    y + r * math.sin(a0 + (a1 - a0) * i / 80)) for i in range(81)]))
        arc_gap = min(min(math.dist(a, b) for a in A for b in B) - w
                      for i, (ka, A) in enumerate(arcs) for kb, B in arcs[i + 1:] if ka != kb)
        ring_gap = min(math.dist(q, (cx, cy)) for _, A in arcs for q in A) - w / 2 - g["ring"][0]
        name = "icon" if icon else "mark"
        print(f"{name}: arc-arc gap {arc_gap:.2f}, arc-ring gap {ring_gap:.2f}")
        assert arc_gap >= MIN_GAP and ring_gap >= MIN_GAP, f"{name}: clearance below {MIN_GAP}"


# ------------------------------------------------------------ lettering ---

@lru_cache
def font(name: str) -> TTFont:
    path = subprocess.run(["kpsewhich", name], capture_output=True, text=True).stdout.strip()
    if not path:
        raise FileNotFoundError(f"kpsewhich cannot find {name}")
    return TTFont(path)


def _pair_kern(f: TTFont, left: str, right: str) -> int:
    """Horizontal pair adjustment from the GPOS 'kern' feature (PairPos 1/2)."""
    if "GPOS" not in f:
        return 0
    table = f["GPOS"].table
    idx = sorted({i for fr in table.FeatureList.FeatureRecord if fr.FeatureTag == "kern"
                  for i in fr.Feature.LookupListIndex})
    for li in idx:
        lookup = table.LookupList.Lookup[li]
        for st in lookup.SubTable:
            if lookup.LookupType == 9:
                st = st.ExtSubTable
            if getattr(st, "LookupType", 2) != 2 or left not in st.Coverage.glyphs:
                continue
            if st.Format == 1:
                ps = st.PairSet[st.Coverage.glyphs.index(left)]
                for rec in ps.PairValueRecord:
                    if rec.SecondGlyph == right and rec.Value1 is not None:
                        return getattr(rec.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs.get(left, 0)
                c2 = st.ClassDef2.classDefs.get(right, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                adv = getattr(v, "XAdvance", 0) if v is not None else 0
                if adv:
                    return adv
    return 0


def text_path(font_name: str, text: str, size: float, x: float, baseline: float,
              tracking: float = 0.0) -> tuple[str, float, tuple]:
    """Outline `text` as one SVG path string. Returns (d, advance width, ink bbox)."""
    f = font(font_name)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    s = size / f["head"].unitsPerEm
    names = [cmap[ord(c)] for c in text]
    pen = SVGPathPen(gs, ntos=n)
    bounds = BoundsPen(gs)
    cursor = 0.0
    for i, name in enumerate(names):
        m = (s, 0, 0, -s, x + cursor, baseline)
        gs[name].draw(TransformPen(pen, m))
        gs[name].draw(TransformPen(bounds, m))
        cursor += f["hmtx"][name][0] * s
        if i + 1 < len(names):
            cursor += _pair_kern(f, name, names[i + 1]) * s + tracking * size
    return pen.getCommands(), cursor, bounds.bounds


def cap_height(font_name: str) -> float:
    f = font(font_name)
    return f["OS/2"].sCapHeight / f["head"].unitsPerEm


# -------------------------------------------------------------- lockups ---

def lockup(p, tagline: bool) -> tuple[str, tuple]:
    """Mark left, wordmark right (mark height 100). Returns (markup, ink viewBox)."""
    x = 120  # mark grid (100) + gap (20)
    cap, base = (36.0, 56.0) if tagline else (40.0, 70.0)
    d, _, bb = text_path(WORDMARK_FONT, "HYMN", cap / cap_height(WORDMARK_FONT), x, base,
                         tracking=0.02)
    shift = x - bb[0]  # align the ink edge of the H with x
    parts = [mark(p), f'<path transform="translate({n(shift)} 0)" d="{d}" fill="{p["ink"]}"/>']
    x0, y0, x1, y1 = geometry()[3]
    x1, y0, y1 = max(x1, bb[2] + shift), min(y0, bb[1]), max(y1, bb[3])
    if tagline:
        # set the expansion to the width of the wordmark
        _, _, pb = text_path(TAGLINE_FONT, TAGLINE, 10, 0, 0, tracking=0.01)
        t_size = 10 * (bb[2] - bb[0]) / (pb[2] - pb[0])
        td, _, tb = text_path(TAGLINE_FONT, TAGLINE, t_size, x, 79, tracking=0.01)
        parts.append(f'<path transform="translate({n(x - tb[0])} 0)" d="{td}" fill="{p["ink2"]}"/>')
        x1, y1 = max(x1, tb[2] + x - tb[0]), max(y1, tb[3])
    return "".join(parts), (x0, y0, x1 - x0, y1 - y0)


def svg(inner: str, box: tuple) -> str:
    vb = " ".join(n(v) for v in box)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" '
            f'aria-label="{TITLE}"><title>{TITLE}</title>{inner}</svg>\n')


def inline_mark() -> str:
    """Topbar snippet: the mark coloured by the page's CSS tokens.

    var() goes into style attributes, because presentation attributes with var()
    are not reliable across browsers. The page keeps the text "HYMN" next to it,
    so the SVG is hidden from assistive technology.
    """
    inner = re.sub(r'(fill|stroke)="(var\(--[\w-]+\))"', r'style="\1:\2"', mark(PALETTES["css"]))
    return (f'<svg class="brand-mark" viewBox="0 0 100 100" aria-hidden="true" '
            f'focusable="false">{inner}</svg>\n')


def build() -> dict[str, str]:
    """Write the SVGs. Returns the standalone ones (not the inline snippet) by name."""
    files = {"hymn-icon.svg": svg(mark(PALETTES["tile"], icon=True), (0, 0, 100, 100)),
             "hymn-icon-full.svg": svg(mark(PALETTES["tile"], icon=True, radius=0),
                                       (0, 0, 100, 100))}
    for suffix, pal in [("", "light"), ("-dark", "dark"), ("-white", "white")]:
        p = PALETTES[pal]
        files[f"hymn-mark{suffix}.svg"] = svg(mark(p), (0, 0, 100, 100))
        files[f"hymn-logo{suffix}.svg"] = svg(*lockup(p, tagline=True))
        files[f"hymn-logo-compact{suffix}.svg"] = svg(*lockup(p, tagline=False))
    OUT.mkdir(exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    (OUT / "hymn-mark-inline.svg").write_text(inline_mark(), encoding="utf-8")
    return files


def export(files: dict[str, str]) -> int:
    """Apple touch icon (180 px PNG) and PDFs of all marks and lockups via PyMuPDF.

    The PDF page is the SVG viewBox. The lockups stay cropped to ink, so
    `height=` in LaTeX means the visible height, and the marks keep their
    100 x 100 square. Returns the number of PDFs.
    """
    import fitz

    page = fitz.open(stream=files["hymn-icon-full.svg"].encode(), filetype="svg")[0]
    zoom = 180 / page.rect.height
    page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).save(OUT / "apple-touch-icon.png")
    pdf = OUT / "pdf"
    pdf.mkdir(exist_ok=True)
    names = [name for name in files if not name.startswith("hymn-icon")]
    for name in names:
        doc = fitz.open(stream=files[name].encode(), filetype="svg")
        (pdf / f"{Path(name).stem}.pdf").write_bytes(doc.convert_to_pdf())
    return len(names)


def render_pngs(files: dict[str, str]) -> None:
    """Control renderings via PyMuPDF on the background each variant is made for."""
    import fitz

    png = OUT / "png"
    png.mkdir(exist_ok=True)
    for name, text in files.items():
        bg = "#0d0d0d" if "-dark" in name else "#0a777f" if "-white" in name else "#f9f9f7"
        if not name.startswith("hymn-icon"):
            head, body = text.split(">", 1)
            x, y, w, h = head.split('viewBox="')[1].split('"')[0].split()
            text = f'{head}><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>{body}'
        page = fitz.open(stream=text.encode(), filetype="svg")[0]
        for px in ([16, 32, 180, 512] if "mark" in name or "icon" in name else [48, 400]):
            zoom = px / page.rect.height
            page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).save(
                png / f"{Path(name).stem}-{px}.png")


if __name__ == "__main__":
    check_clearances()
    files = build()
    n_pdf = export(files)
    if "--png" in sys.argv:
        render_pngs(files)
    print(f"wrote {len(files) + 1} SVGs, apple-touch-icon.png and {n_pdf} PDFs to {OUT}")
