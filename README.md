# HYMN project page

Source of the project page for **HYMN (HYbrid Multi-technology Navigation)**, a
multi-technology radio positioning dataset, and the studies built on it. The page
is a single static HTML file served by GitHub Pages. There is no build step on
GitHub. The scripts in `tools/` regenerate figures and the site map locally.

Live page: `https://paulschwarzbach.github.io/hymn/`

## Layout

```
index.html              the page (site map SVG injected between SITEMAP markers)
assets/css/style.css    all styles, light and dark
assets/js/main.js       copy buttons, map tooltips and layer toggles (optional)
assets/fonts/           Inter and Source Serif 4, latin subsets, SIL OFL 1.1
assets/fig/             paper figures converted to SVG
assets/img/             photos, orthophoto, favicon, touch icon, Open Graph image
brand/make_logo.py      HYMN logo generator, the canonical source of the logo
brand/logo/             logo SVGs, PDFs (pdf/) and apple-touch-icon.png, all generated
tools/build_assets.py   photos and paper figures from their original sources
tools/make_site_map.py  site map from the HYMN reference CSVs + GeoSN orthophoto
tools/make_og.py        Open Graph image and GitHub social previews (headless Edge/Chrome)
```

Other repositories that show the logo (README banners of `HYMN-dataset` and
`hymn-localization-ipin2026`, the IPIN 2026 slides) copy files from `brand/logo/`.
Change the logo only in `brand/make_logo.py`, never in the SVGs.

Local-only folders (gitignored): `_src/` caches extracted originals and screenshots,
`_incoming/` receives new photos.

## Rebuild

Requires Python 3.11+, `numpy`, `Pillow`, `PyMuPDF`, and Poppler's `pdftocairo`.
The logo also needs `fontTools` and Source Serif 4 from a TeX distribution
(found via `kpsewhich`).
Paths to the source projects are resolved relative to the folder that holds
`hymn-localization`, `indoor-outdoor-localization` and `HYMN-dataset`.

```bash
python brand/make_logo.py                     # logo; --png adds control renderings
python tools/build_assets.py                  # photos and paper figures
python tools/make_site_map.py                 # site map -> index.html, assets/img/site-ortho.webp
python -m http.server 8765                    # preview at http://127.0.0.1:8765/
python tools/make_og.py                       # needs the server above
python tools/make_og.py --social              # GitHub social previews -> _src/social/
```

After a logo change, copy `brand/logo/hymn-icon.svg` to `assets/img/favicon.svg`,
`brand/logo/apple-touch-icon.png` to `assets/img/`, paste
`brand/logo/hymn-mark-inline.svg` into the `.brand` link and the `h1` of
`index.html`, raise the `?v=` suffix of both icon links in `<head>` so browsers
drop their cached icon, and rerun `make_og.py`.

## Updating

| Event | Change |
|---|---|
| New photos | Drop JPEGs into `_incoming/` or `assets/img/`, run `python tools/build_assets.py photos` (originals move to `_src/originals/`), add `<figure class="photo">` blocks to the `env-photos` card next to the site map, with alt text, caption and credit. EXIF (incl. GPS) is stripped. |
| IPIN preprint online | Replace the `link-pending` span in the IPIN card with the arXiv link and add `eprint`/`doi` to the IPIN BibTeX. |
| After 7 Oct 2026 | Change the IPIN status line from "talk on" to "presented", later add the IEEE DOI. |
| Any edit | Update the "Last updated" date in the footer. |

## Deploy (first time)

1. Replace the placeholder with the GitHub username:
   `sed -i 's/PaulSchwarzbach/<username>/g' index.html README.md`
2. Create an empty public repository `hymn` on that account.
3. Set a repository-local identity so commits are attributed to the private account:
   `git config user.name "Paul Schwarzbach"` and
   `git config user.email "<id>+<username>@users.noreply.github.com"`
4. `git remote add origin https://<username>@github.com/<username>/hymn.git`,
   commit, `git push -u origin main`.
5. Repository Settings → Pages → Deploy from a branch → `main` / root.

## Provenance

Every figure, number and venue string on the page comes from one of the sources
below. Paths are relative to the local project folders.

### Assets

| Asset | Source | Publication |
|---|---|---|
| `assets/img/plate.webp` | `indoor-outdoor-localization`, `origin/main:Coordinates/4032-3024-max.jpg`, cropped | Descriptor Fig. 1, PLANS 2025 Fig. 4 |
| `assets/img/gate-outside.webp` | Paul Schwarzbach, `PXL_20241022_162659224.MP.jpg` (Pixel 6a, 22 Oct 2024 18:26 local), number plate blurred, EXIF stripped | unpublished |
| `assets/img/hall-overview.webp` | Paul Schwarzbach, `IMG_5553_Überblick2.JPEG` (iPhone 14 Pro, 13 Mar 2025), EXIF stripped | unpublished |
| `assets/img/hall.webp` | `ION_IEEE_PLANS_2025_Full_Paper.pdf`, p. 4 embedded image, number plate blurred | PLANS 2025 Fig. 3 |
| `assets/img/site-ortho.webp` | GeoSN WMS `sn_dop_020` (Quelle: GeoSN, dl-de/by-2-0), resampled to the local frame | none |
| site map markers | `HYMN-dataset/data/reference/csv/{point,anchor}_coordinates.csv`, local frame | none |
| `assets/fig/ipin-ecdf-fused.svg` | `hymn-localization/Paper/fig/ecdf_fused.pdf` | IPIN 2026 Fig. 3 |
| `assets/fig/icra-ecdf-residuals.svg` | `ICRA/figures/paper_fig3_ecdf.pdf` | ICRA 2026 WS Fig. 5 |
| `assets/fig/plans-position-errors.svg` | `ION_IEEE_PLANS_2025_Full_Paper.pdf`, p. 10, vector crop | PLANS 2025 Fig. 14 |
| topbar and hero mark in `index.html` | `brand/logo/hymn-mark-inline.svg`, colours from the CSS tokens | none |
| `assets/img/favicon.svg`, `assets/img/apple-touch-icon.png` | copies of `brand/logo/hymn-icon.svg` and `brand/logo/apple-touch-icon.png` | none |
| `assets/img/og-image.png` | `tools/make_og.py` from `brand/logo/hymn-logo.svg` and the site map | none |

### Facts and numbers

| On the page | Source |
|---|---|
| Acronym, hall 44 m × 18 m, Torgau, driveway with gates | `HYMN/Data Descriptor/main_rr1.tex` l. 36, 87 |
| Systems table: infrastructure hardware, counts, principles | `main_rr1.tex` l. 65–70 (Table 1). 5G NR principle given as fingerprinting (SNR) without TDOA, per Paul Schwarzbach (2026-09-28) |
| Infrastructure nouns (anchors, beacons, access points, radio units) | IPIN `methodology.tex` §III-A, raw log headers (`wifi` AP1–AP6, `nr5g` SNR RU1–RU3) |
| Mobile units: 2 UWB tags, smartphone, 5G NR antenna, GNSS receiver, prism | `main_rr1.tex` l. 93, PLANS 2025 §II |
| BLE tag and beacons Metirionic DMK-215 | Paul Schwarzbach (2026-09-28), raw BLE logs (`"message": "Metirionic rf215"`) |
| Smartphone model Google Pixel 6a | Paul Schwarzbach, 2026-09-28 |
| GNSS constellations GPS, GLONASS, Galileo, BeiDou | `data/raw/gnss/all.24O` header (SYS / # / OBS TYPES) |
| 48 points, 3 min static, plate | `main_rr1.tex` l. 130 |
| TS16, millimetre-level survey of points and anchors | `main_rr1.tex` l. 193, IPIN `methodology.tex` §III-A |
| Recording date, point windows | `HYMN-dataset/data/reference/csv/time_reference.csv` |
| GNSS only at the 12 driveway points | RINEX `data/raw/gnss/all.24O` header (15:39:41–16:36:28 GPS) vs. `time_reference.csv` (hall grid 12:28–15:19 UTC) |
| 5G NR as SNR and positions | `HYMN-dataset/data/processed/README.md`, PLANS 2025 §II |
| Point groups A02–A13 / A01 / T01–T06 | `point_coordinates.csv` (asserted 36/6/6 in `make_site_map.py`) |
| Funding IDEA (FKZ 19OI22020C), MRK facility access | `main_rr1.tex` l. 465, PLANS 2025 acknowledgment |
| Descriptor vol. 3, pp. 379–387, CC BY 4.0 | Crossref record of 10.1109/IEEEDATA.2026.3691044 |
| Dataset v1.0.0 on 2025-12-18 | Zenodo record 17979436 |
| Code DOI = v1.1-ipin2026 | Zenodo record 20058106 |
| IPIN medians and P95 | `hymn-localization/Paper/sections/conclusion.tex` l. 4, 6, `evaluation.tex` §IV |
| IPIN venue, session, 7 Oct 2026 | IPIN 2026 conference programme |
| ICRA UWB P95 0.99 / 3.70 m, WiFi bias 1.17 / 5.94 m | `ICRA/figures/table1_residuals.tex` l. 15–25 |
| ICRA headline (transition zone) | `ICRA/root.tex` l. 384 |
| ICRA workshop name, date, place | robotmeetsranging.tech |
| PLANS findings | `ION_IEEE_PLANS_2025_Full_Paper.pdf` §IV-C, §IV-D, Table II |
| PLANS pages 948–959, 28 Apr – 1 May 2025, Salt Lake City | Crossref record of 10.1109/PLANS61210.2025.11028349 |

The page deliberately avoids:
- comparing ranging residuals across studies, because their definitions differ,
- any number the papers do not print (e.g. values read off figures).

## Licence

Page text CC BY 4.0, page code MIT (see `LICENSE`). Figures and photos belong to
their publications and are credited in place. Fonts are under the SIL Open Font
License 1.1 (`assets/fonts/OFL-*.txt`). Orthophoto: Quelle: GeoSN, dl-de/by-2-0.
`brand/make_logo.py` is MIT. The HYMN logo may be used unmodified to refer to HYMN.
