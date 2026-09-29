"""Render the Open Graph preview image (assets/img/og-image.png, 1200x630).

Builds a small HTML page from the site map already injected into index.html and
screenshots it with a headless Chromium browser (Edge or Chrome). The page must
be served from the landing-page root, e.g. `python -m http.server 8765`.

Usage: python tools/make_og.py [--browser PATH] [--port 8765]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "msedge",
]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  :root {{ color-scheme: light; }}
  html, body {{ margin: 0; width: 1200px; height: 630px; overflow: hidden; background: #f9f9f7; color: #0b0b0b; }}
  .og {{ display: grid; grid-template-columns: 560px 1fr; gap: 48px; align-items: center; height: 630px; padding: 0 56px; box-sizing: border-box; }}
  .og h1 {{ font-size: 104px; margin: 0 0 12px; }}
  .og .expansion {{ font-size: 30px; color: #52514e; margin-top: 14px; }}
  .og p {{ font-size: 26px; line-height: 1.4; color: #0b0b0b; margin: 28px 0 0; }}
  .og .map-wrap {{ border-radius: 14px; box-shadow: 0 0 0 1px rgba(11,11,11,.1); }}
  .sm-veil {{ fill: #fcfcfb !important; opacity: .18 !important; }}
</style></head><body><div class="og">
<div><h1>HYMN <span class="expansion">HYbrid Multi-technology Navigation</span></h1>
<p>UWB, BLE, WiFi FTM, 5G NR and GNSS with total-station ground truth across an indoor-outdoor transition.</p></div>
<div class="map-wrap">{svg}</div></div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    svg = re.search(r'<svg class="sitemap".*?</svg>', html, re.S).group(0)
    svg = svg.replace('href="assets/', 'href="/assets/')
    tmp = ROOT / "_src" / "og.html"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(PAGE.format(svg=svg), encoding="utf-8")

    browser = args.browser or next(
        (c for c in CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    if browser is None:
        raise SystemExit("no Chromium-based browser found, pass --browser")
    out = ROOT / "assets" / "img" / "og-image.png"
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--blink-settings=preferredColorScheme=1", "--window-size=1200,630",
                    "--virtual-time-budget=4000", f"--screenshot={out}",
                    f"http://127.0.0.1:{args.port}/_src/og.html"],
                   check=True, capture_output=True)
    print("wrote", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
