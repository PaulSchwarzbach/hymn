"""Generate the interactive site map for the HYMN landing page.

Reads the public HYMN reference coordinates, fetches the GeoSN digital
orthophoto (DOP 20 cm, dl-de/by-2-0) for the campaign area, resamples it into
the dataset's local frame, and writes

  assets/img/site-ortho.webp   orthophoto, rotated to the local frame
  index.html                   inline SVG between <!-- SITEMAP:START/END -->

The map is drawn in the local frame of the dataset with the hall's long axis
(local y) running left to right: screen u = y_local, screen v = x_local.
This is a pure rotation of the frame, not a mirror.

Usage (from the landing-page root):
    python tools/make_site_map.py --dataset ../../HYMN-dataset
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

# Local -> UTM33N (EPSG:25833), from HYMN-dataset/data/reference/README.md
R = np.array([[-0.84645628, 0.53245822], [-0.53245822, -0.84645628]])
T = np.array([361620.04024452, 5715157.13887458])

WMS = ("https://geodienste.sachsen.de/wms_geosn_dop-rgb/guest?SERVICE=WMS&VERSION=1.3.0"
       "&REQUEST=GetMap&CRS=EPSG:25833&LAYERS=sn_dop_020&STYLES=&FORMAT=image/png"
       "&BBOX={e0},{n0},{e1},{n1}&WIDTH={w}&HEIGHT={h}")

MARGIN = 4.0          # m around the outermost point/anchor
ORTHO_RES = 0.04      # m per output pixel
WMS_RES = 0.10        # m per requested WMS pixel (DOP native is 0.20 m)
SITE_STEP = 1.6       # m between co-located anchor glyphs
POINT_R = 0.6         # m, reference-point marker radius

TECH = {  # dataset prefix -> (css key, label)
    "UWB": ("uwb", "UWB"),
    "BLE": ("ble", "BLE"),
    "WIFI": ("wifi", "WiFi FTM"),
    "NR5G": ("nr5g", "5G NR"),
}
NOUN = {"uwb": "UWB anchor", "ble": "BLE beacon", "wifi": "WiFi access point", "nr5g": "5G NR radio unit"}
TECH_ORDER = ["uwb", "ble", "wifi", "nr5g"]


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def local_to_utm(x: float, y: float) -> np.ndarray:
    return R @ np.array([x, y]) + T


def point_group(pid: str) -> tuple[str, str]:
    if pid.startswith("T"):
        return "out", "outside the gates"
    if pid.startswith("A01"):
        return "gate", "driveway row inside the hall"
    return "hall", "hall grid"


def load(dataset: Path):
    ref = dataset / "data" / "reference" / "csv"
    anchors, points = [], []
    for r in read_csv(ref / "anchor_coordinates.csv"):
        x, y, z = float(r["X_LOCAL"]), float(r["Y_LOCAL"]), float(r["Z_LOCAL"])
        err = np.hypot(*(local_to_utm(x, y) - [float(r["E"]), float(r["N"])]))
        assert err < 0.05, f"{r['point_id']}: local/UTM mismatch {err:.3f} m"
        tech = TECH[r["point_id"].split("_")[0]][0]
        anchors.append(dict(id=r["point_id"], tech=tech, x=x, y=y, z=z))
    for r in read_csv(ref / "point_coordinates.csv"):
        x, y = float(r["X_LOCAL_CENTER"]), float(r["Y_LOCAL_CENTER"])
        err = np.hypot(*(local_to_utm(x, y) - [float(r["E_CENTER"]), float(r["N_CENTER"])]))
        assert err < 0.05, f"{r['point_id']}: local/UTM mismatch {err:.3f} m"
        g, glabel = point_group(r["point_id"])
        points.append(dict(id=r["point_id"], x=x, y=y, group=g, glabel=glabel))
    counts = {g: sum(p["group"] == g for p in points) for g in ("hall", "gate", "out")}
    assert counts == {"hall": 36, "gate": 6, "out": 6}, counts
    return anchors, points


def view_extent(anchors, points):
    us = [a["y"] for a in anchors] + [p["y"] for p in points] + [0.0]
    vs = [a["x"] for a in anchors] + [p["x"] for p in points] + [0.0]
    u0, u1 = np.floor(min(us) - MARGIN), np.ceil(max(us) + MARGIN)
    v0, v1 = np.floor(min(vs) - MARGIN), np.ceil(max(vs) + MARGIN)
    return float(u0), float(v0), float(u1 - u0), float(v1 - v0)


def fetch_ortho(u0, v0, w, h, cache: Path) -> Path:
    corners = [local_to_utm(v, u) for u in (u0, u0 + w) for v in (v0, v0 + h)]
    e0 = np.floor(min(c[0] for c in corners)) - 5
    e1 = np.ceil(max(c[0] for c in corners)) + 5
    n0 = np.floor(min(c[1] for c in corners)) - 5
    n1 = np.ceil(max(c[1] for c in corners)) + 5
    wpx, hpx = int(round((e1 - e0) / WMS_RES)), int(round((n1 - n0) / WMS_RES))
    raw = cache / f"geosn_dop_{int(e0)}_{int(n0)}_{int(e1)}_{int(n1)}.png"
    if not raw.exists():
        url = WMS.format(e0=e0, n0=n0, e1=e1, n1=n1, w=wpx, h=hpx)
        print("fetching", url)
        data = urllib.request.urlopen(url, timeout=60).read()
        Image.open(io.BytesIO(data)).verify()
        raw.write_bytes(data)
    img = Image.open(raw).convert("RGB")

    # Output pixel (i, j) -> local (u = y, v = x) -> UTM -> WMS pixel (affine).
    s, rin = ORTHO_RES, WMS_RES
    a = R[0, 1] * s / rin
    b = R[0, 0] * s / rin
    c = (R[0, 0] * v0 + R[0, 1] * u0 + T[0] - e0) / rin
    d = -R[1, 1] * s / rin
    e = -R[1, 0] * s / rin
    f = (n1 - (R[1, 0] * v0 + R[1, 1] * u0 + T[1])) / rin
    out = img.transform((int(round(w / s)), int(round(h / s))), Image.AFFINE,
                        (a, b, c, d, e, f), resample=Image.BICUBIC)
    dst = ROOT / "assets" / "img" / "site-ortho.webp"
    out.save(dst, "WEBP", quality=80, method=6)
    print("wrote", dst, out.size, dst.stat().st_size // 1024, "KB")
    return dst


# ---------------------------------------------------------------- SVG glyphs
def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def glyph(tech: str, u: float, v: float) -> str:
    s = 0.75  # half size in m
    if tech == "uwb":
        pts = [(u, v - s * 1.1), (u + s, v + s * 0.75), (u - s, v + s * 0.75)]
        return f'<polygon points="{" ".join(f"{f(a)},{f(b)}" for a, b in pts)}"/>'
    if tech == "ble":
        pts = [(u, v - s), (u + s, v), (u, v + s), (u - s, v)]
        return f'<polygon points="{" ".join(f"{f(a)},{f(b)}" for a, b in pts)}"/>'
    if tech == "wifi":
        k = s * 0.8
        return f'<rect x="{f(u - k)}" y="{f(v - k)}" width="{f(2 * k)}" height="{f(2 * k)}" rx="0.12"/>'
    if tech == "nr5g":
        pts = [(u + s * np.cos(t), v + s * np.sin(t)) for t in np.radians(np.arange(0, 360, 60))]
        return f'<polygon points="{" ".join(f"{f(a)},{f(b)}" for a, b in pts)}"/>'
    raise ValueError(tech)


def build_svg(anchors, points, u0, v0, w, h) -> str:
    L = []
    L.append(f'<svg class="sitemap" viewBox="{f(u0)} {f(v0)} {f(w)} {f(h)}" role="img" '
             f'aria-labelledby="sitemap-title sitemap-desc" xmlns="http://www.w3.org/2000/svg">')
    L.append('<title id="sitemap-title">HYMN campaign layout on an orthophoto</title>')
    L.append('<desc id="sitemap-desc">Reference points and infrastructure of the HYMN campaign in '
             'the local frame of the dataset, drawn over the GeoSN orthophoto of the site. '
             'The hall extends to the right, the driveway crosses it near the left edge, and '
             'six reference points lie on the driveway outside the gates.</desc>')
    L.append(f'<image href="assets/img/site-ortho.webp" x="{f(u0)}" y="{f(v0)}" width="{f(w)}" '
             f'height="{f(h)}" preserveAspectRatio="none"/>')
    L.append(f'<rect class="sm-veil" x="{f(u0)}" y="{f(v0)}" width="{f(w)}" height="{f(h)}"/>')

    # Reference points
    L.append('<g class="sm-points">')
    for p in sorted(points, key=lambda p: p["id"]):
        tip = f'{p["id"]} · {p["glabel"]} · x {p["x"]:.2f} m, y {p["y"]:.2f} m'
        cls = f'sm-pt sm-pt-{p["group"]}'
        inner = (f'<circle class="sm-hit" cx="{f(p["y"])}" cy="{f(p["x"])}" r="1.1"/>'
                 f'<circle cx="{f(p["y"])}" cy="{f(p["x"])}" r="{POINT_R}"/>')
        if p["group"] == "out":
            inner += f'<circle class="sm-dot" cx="{f(p["y"])}" cy="{f(p["x"])}" r="0.22"/>'
        L.append(f'<g class="{cls}" data-tip="{tip}"><title>{tip}</title>{inner}</g>')
    L.append('</g>')

    # Infrastructure, grouped by horizontal site (co-located devices drawn side by side)
    sites: list[list[dict]] = []
    for a in sorted(anchors, key=lambda a: (TECH_ORDER.index(a["tech"]), a["id"])):
        for s in sites:
            if np.hypot(s[0]["x"] - a["x"], s[0]["y"] - a["y"]) < 0.25:
                s.append(a)
                break
        else:
            sites.append([a])
    L.append('<g class="sm-anchors">')
    for s in sites:
        s.sort(key=lambda a: TECH_ORDER.index(a["tech"]))
        cu = np.mean([a["y"] for a in s])
        cv = np.mean([a["x"] for a in s])
        offs = (np.arange(len(s)) - (len(s) - 1) / 2) * SITE_STEP
        for a, du in zip(s, offs):
            tip = f'{a["id"]} · {NOUN[a["tech"]]} · height {a["z"]:.2f} m'
            L.append(f'<g class="sm-an sm-{a["tech"]}" data-tip="{tip}"><title>{tip}</title>'
                     f'<circle class="sm-hit" cx="{f(cu + du)}" cy="{f(cv)}" r="0.9"/>'
                     f'{glyph(a["tech"], cu + du, cv)}</g>')
    L.append('</g>')

    # Total station at the local origin
    tip = "Total station (Leica TS16) · origin of the local frame"
    L.append(f'<g class="sm-ts" data-tip="{tip}"><title>{tip}</title>'
             '<circle class="sm-hit" cx="0" cy="0" r="1.1"/>'
             '<circle cx="0" cy="0" r="0.7"/><path d="M-0.7 0H0.7M0 -0.7V0.7"/></g>')

    # Labels for the two groups of points outside the gates
    for side in (-1, 1):
        grp = sorted((p for p in points if p["group"] == "out" and np.sign(p["x"]) == side),
                     key=lambda p: p["id"])
        lu = max(p["y"] for p in grp) + POINT_R + 0.9
        lv = np.mean([p["x"] for p in grp]) + 0.5
        L.append(f'<text class="sm-label" x="{f(lu)}" y="{f(lv)}">{grp[0]["id"]}–{grp[-1]["id"]}</text>')

    # North arrow (top right) and 10 m scale bar (bottom left)
    north = np.array([R[1, 1], R[1, 0]])  # local (y, x) of unit north -> screen (u, v)
    ang = np.degrees(np.arctan2(north[0], -north[1]))
    nx, ny = u0 + w - 3.2, v0 + 3.4
    tip_u, tip_v = nx + 3.1 * np.sin(np.radians(ang)), ny - 3.1 * np.cos(np.radians(ang))
    L.append(f'<g class="sm-chrome sm-north"><path transform="translate({f(nx)} {f(ny)}) rotate({ang:.1f})" '
             'd="M0 1.7V-1.7M-0.75 -0.85L0 -1.8L0.75 -0.85"/>'
             f'<text x="{f(tip_u)}" y="{f(tip_v + 0.5)}" text-anchor="middle">N</text></g>')
    sx, sy = u0 + 2.0, v0 + h - 2.0
    L.append(f'<g class="sm-chrome sm-scale"><path d="M{f(sx)} {f(sy)}h10"/>'
             f'<path d="M{f(sx)} {f(sy - 0.5)}v1M{f(sx + 5)} {f(sy - 0.3)}v0.6M{f(sx + 10)} {f(sy - 0.5)}v1"/>'
             f'<text x="{f(sx + 5)}" y="{f(sy - 0.9)}" text-anchor="middle">10 m</text></g>')
    L.append('</svg>')
    return "\n".join(L)


def inject(svg: str, html: Path) -> None:
    text = html.read_text(encoding="utf-8")
    pat = re.compile(r"(<!-- SITEMAP:START -->)(.*?)(<!-- SITEMAP:END -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"markers not found in {html}")
    html.write_text(pat.sub(lambda m: m.group(1) + "\n" + svg + "\n" + m.group(3), text),
                    encoding="utf-8")
    print("injected site map into", html)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, default=ROOT.parents[1] / "HYMN-dataset")
    ap.add_argument("--cache", type=Path, default=ROOT / "_src")
    args = ap.parse_args()
    args.cache.mkdir(exist_ok=True)
    anchors, points = load(args.dataset)
    u0, v0, w, h = view_extent(anchors, points)
    print(f"view u {u0}..{u0 + w}  v {v0}..{v0 + h}  ({w} x {h} m)")
    fetch_ortho(u0, v0, w, h, args.cache)
    inject(build_svg(anchors, points, u0, v0, w, h), ROOT / "index.html")


if __name__ == "__main__":
    main()
