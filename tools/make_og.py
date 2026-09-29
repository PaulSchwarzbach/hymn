"""Render the Open Graph preview image (assets/img/og-image.png, 1200x630).

Builds a small HTML page from the logo (brand/logo/hymn-logo.svg) and the site
map already injected into index.html and screenshots it with a headless
Chromium browser (Edge or Chrome). The page must be served from the
landing-page root, e.g. `python -m http.server 8765`.

With --social it renders the GitHub social previews of the two TUD-ITVS
repositories instead (1280x640, to _src/social/). GitHub has no API for them,
so they are uploaded by hand under Settings, Social preview.

Usage: python tools/make_og.py [--social] [--browser PATH] [--port 8765]
"""

from __future__ import annotations

import argparse
import html
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

OG_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  :root {{ color-scheme: light; }}
  html, body {{ margin: 0; width: 1200px; height: 630px; overflow: hidden; background: #f9f9f7; color: #0b0b0b; }}
  .og {{ display: grid; grid-template-columns: 560px 1fr; gap: 48px; align-items: center; height: 630px; padding: 0 56px; box-sizing: border-box; }}
  .og .logo {{ width: 500px; height: auto; }}
  .og p {{ font-size: 26px; line-height: 1.4; color: #0b0b0b; margin: 36px 0 0; }}
  .og .map-wrap {{ border-radius: 14px; box-shadow: 0 0 0 1px rgba(11,11,11,.1); }}
  .sm-veil {{ fill: #fcfcfb !important; opacity: .18 !important; }}
</style></head><body><div class="og">
<div><img class="logo" src="/brand/logo/hymn-logo.svg" alt="">
<p>UWB, BLE, WiFi FTM, 5G NR and GNSS with total-station ground truth across an indoor-outdoor transition.</p></div>
<div class="map-wrap">{svg}</div></div></body></html>"""

SOCIAL_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="/assets/css/style.css">
<style>
  :root {{ color-scheme: light; }}
  html, body {{ margin: 0; width: 1280px; height: 640px; overflow: hidden; background: #f9f9f7; color: #0b0b0b; }}
  .social {{ display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 48px; height: 640px; padding: 0 120px; box-sizing: border-box; text-align: center; }}
  .social .logo {{ width: 620px; height: auto; }}
  .social .repo {{ font: 600 34px/1.2 var(--sans); color: #0b0b0b; margin: 0; }}
  .social p {{ font-size: 24px; line-height: 1.45; color: #52514e; margin: 14px 0 0; }}
</style></head><body><div class="social">
<img class="logo" src="/brand/logo/hymn-logo.svg" alt="">
<div><p class="repo">{repo}</p><p>{desc}</p></div></div></body></html>"""

# repository descriptions as set under About on GitHub (2026-09-29)
SOCIAL = {
    "HYMN-dataset": (
        "TUD-ITVS/HYMN-dataset",
        "Multi-technology wireless positioning dataset (WiFi/BLE/UWB/GNSS/5G NR) with reference "
        "data, processed measurements, and optional preprocessing scripts."),
    "hymn-localization-ipin2026": (
        "TUD-ITVS/hymn-localization-ipin2026",
        "Companion code for the IPIN 2026 paper benchmarking iterative least squares, robust least "
        "squares, Bayesian grid filtering, and ResNet on the HYMN multi-technology dataset."),
}


def find_browser(explicit: str | None) -> str:
    browser = explicit or next(
        (c for c in CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    if browser is None:
        raise SystemExit("no Chromium-based browser found, pass --browser")
    return browser


def screenshot(browser: str, page: str, markup: str, size: tuple[int, int], out: Path,
               port: int) -> None:
    """Write `markup` to _src/<page> and screenshot it from the local server in light mode."""
    tmp = ROOT / "_src" / page
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(markup, encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--blink-settings=preferredColorScheme=1", f"--window-size={size[0]},{size[1]}",
                    "--virtual-time-budget=4000", f"--screenshot={out}",
                    f"http://127.0.0.1:{port}/_src/{page}"],
                   check=True, capture_output=True)
    print("wrote", out, out.stat().st_size // 1024, "KB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--social", action="store_true")
    ap.add_argument("--browser")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    browser = find_browser(args.browser)

    if args.social:
        for name, (repo, desc) in SOCIAL.items():
            screenshot(browser, f"social-{name}.html",
                       SOCIAL_PAGE.format(repo=html.escape(repo), desc=html.escape(desc)),
                       (1280, 640), ROOT / "_src" / "social" / f"{name}.png", args.port)
        return

    page = (ROOT / "index.html").read_text(encoding="utf-8")
    svg = re.search(r'<svg class="sitemap".*?</svg>', page, re.S).group(0)
    svg = svg.replace('href="assets/', 'href="/assets/')
    screenshot(browser, "og.html", OG_PAGE.format(svg=svg), (1200, 630),
               ROOT / "assets" / "img" / "og-image.png", args.port)


if __name__ == "__main__":
    main()
