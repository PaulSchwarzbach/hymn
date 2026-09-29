"""Build the page's figures and photos from their original sources.

Every web asset is derived here from a named source file, so the page can be
rebuilt and each figure traced back to its publication (see README.md).

Requirements: Python 3.11+, Pillow, PyMuPDF, and `pdftocairo` (Poppler, e.g. via
MiKTeX or TeX Live) on PATH.

Usage (from the landing-page root):
    python tools/build_assets.py            # all assets
    python tools/build_assets.py photos     # photos only
    python tools/build_assets.py figures    # paper figures only

Source locations are resolved relative to the parent folder of this checkout
(the local layout of the HYMN projects). Override with --base.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "assets" / "fig"
IMG = ROOT / "assets" / "img"
SRC = ROOT / "_src"          # local cache for extracted originals (gitignored)
INCOMING = ROOT / "_incoming"  # new photos dropped here by the maintainer (gitignored)


def sources(base: Path) -> dict[str, Path]:
    """Original files, relative to the folder that holds the HYMN projects."""
    home = Path.home()
    return {
        # IPIN 2026 paper (this repository's parent)
        "ipin_ecdf": base / "hymn-localization" / "Paper" / "fig" / "ecdf_fused.pdf",
        # ICRA 2026 workshop paper, Fig. 5
        "icra_ecdf": home / "Nextcloud" / "Veröffentlichungen" / "ICRA" / "figures" / "paper_fig3_ecdf.pdf",
        # PLANS 2025 paper (author build), Fig. 3 photo on p. 4, Fig. 14 on p. 10
        "plans_pdf": base / "indoor-outdoor-localization" / "ION_IEEE_PLANS_2025_Full_Paper.pdf",
        # Plate photo original (descriptor Fig. 1 / PLANS Fig. 4), from git history
        "plans_repo": base / "indoor-outdoor-localization",
    }


# ------------------------------------------------------------------ helpers
def save_webp(im: Image.Image, dst: Path, width: int, quality: int = 80) -> None:
    im = ImageOps.exif_transpose(im).convert("RGB")  # drops EXIF (incl. GPS) on save
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)
    print(f"  {dst.relative_to(ROOT)}  {im.size[0]}x{im.size[1]}  {dst.stat().st_size // 1024} KB")


def pdf_to_svg(pdf: Path, dst: Path) -> None:
    subprocess.run(["pdftocairo", "-svg", str(pdf), str(dst)], check=True)
    print(f"  {dst.relative_to(ROOT)}  {dst.stat().st_size // 1024} KB")


def pdf_clip_to_svg(pdf: Path, page: int, clip: tuple[float, float, float, float], dst: Path) -> None:
    """Crop a vector region (PDF points, origin top-left) from one page and convert to SVG."""
    src = fitz.open(pdf)
    rect = fitz.Rect(*clip)
    out = fitz.open()
    out.new_page(width=rect.width, height=rect.height).show_pdf_page(
        fitz.Rect(0, 0, rect.width, rect.height), src, page, clip=rect)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pdf = Path(tmp) / "clip.pdf"
        out.save(tmp_pdf)
        pdf_to_svg(tmp_pdf, dst)


def pdf_to_webp(pdf: Path, dst: Path, width: int, page: int = 0) -> None:
    doc = fitz.open(pdf)
    pg = doc[page]
    zoom = width / pg.rect.width
    pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    save_webp(Image.frombytes("RGB", (pix.width, pix.height), pix.samples), dst, width)


# ------------------------------------------------------------------- photos
def build_photos(src: dict[str, Path]) -> None:
    print("photos")
    SRC.mkdir(exist_ok=True)

    # Measurement plate: original 4032x3024 JPEG from the PLANS repository history.
    plate = SRC / "plate_original.jpg"
    if not plate.exists():
        data = subprocess.run(["git", "-C", str(src["plans_repo"]), "show",
                               "origin/main:Coordinates/4032-3024-max.jpg"],
                              check=True, capture_output=True).stdout
        plate.write_bytes(data)
    im = Image.open(plate)
    w, h = im.size
    im = im.crop((int(0.03 * w), int(0.06 * h), int(0.935 * w), int(0.97 * h)))
    save_webp(im, IMG / "plate.webp", 1400)

    # Hall interior: PLANS Fig. 3, the only available copy (embedded JPEG, 1622x977).
    hall = SRC / "hall_plans_fig3.jpg"
    if not hall.exists():
        doc = fitz.open(src["plans_pdf"])
        # p. 4 also holds the plate photo as two wide strips; Fig. 3 is the ~5:3 image.
        xref = next(i[0] for i in doc[3].get_images(full=True)
                    if i[2] > 1000 and 0.5 < i[3] / i[2] < 0.7)
        hall.write_bytes(doc.extract_image(xref)["image"])
    im = Image.open(hall).convert("RGB")
    im = im.crop((4, 4, im.width - 4, im.height - 4))  # thin border from the paper
    # Blur the vehicle's number plate (x 684-770, y 644-676 in the cropped frame).
    box = (684, 644, 770, 676)
    im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(6)), box)
    save_webp(im, IMG / "hall.webp", 1600)

    # Environment photos supplied by the maintainer (originals kept in _src/originals/).
    env = {
        # Pixel 6a, 22 Oct 2024 18:27 local time: open gate seen from outside
        "PXL_20241022_162659224.MP.jpg": ("gate-outside.webp", (3050, 1945, 3390, 2060)),
        # iPhone 14 Pro, 13 Mar 2025: hall overview, after the campaign
        "IMG_5553_Überblick2.JPEG": ("hall-overview.webp", None),
    }
    originals = SRC / "originals"
    for name, (out, plate_box) in env.items():
        src_file = next((d / name for d in (originals, FIG, IMG, INCOMING) if (d / name).exists()), None)
        if src_file is None:
            print(f"  missing {name}, skipped")
            continue
        im = ImageOps.exif_transpose(Image.open(src_file)).convert("RGB")
        if plate_box:  # blur the vehicle's number plate
            im.paste(im.crop(plate_box).filter(ImageFilter.GaussianBlur(18)), plate_box)
        save_webp(im, IMG / out, 1600)
        if src_file.parent != originals:
            originals.mkdir(parents=True, exist_ok=True)
            src_file.replace(originals / name)
            print(f"  moved original to {(originals / name).relative_to(ROOT)}")

    # New photos from the maintainer, dropped into _incoming/ or straight into
    # assets/img/: resized and saved as .webp with EXIF (incl. GPS) removed. Raw
    # files found in assets/img/ are moved to _src/originals/ so they are never
    # published.
    raw_ext = {".jpg", ".jpeg", ".tif", ".tiff", ".heic"}
    for folder in (INCOMING, IMG):
        for p in sorted(folder.glob("*")):
            if p.suffix.lower() not in raw_ext | ({".png", ".webp"} if folder == INCOMING else set()):
                continue
            save_webp(Image.open(p), IMG / f"photo-{p.stem.lower().replace(' ', '-')}.webp", 1600)
            if folder == IMG:
                originals.mkdir(parents=True, exist_ok=True)
                p.replace(originals / p.name)
                print(f"  moved original to {(originals / p.name).relative_to(ROOT)}")


# ------------------------------------------------------------------ figures
def build_figures(src: dict[str, Path]) -> None:
    print("figures")
    # IPIN 2026, Fig. 3: ECDF of horizontal positioning error on the fused input.
    pdf_to_svg(src["ipin_ecdf"], FIG / "ipin-ecdf-fused.svg")
    # ICRA 2026 WS, Fig. 5: ECDFs of absolute ranging residuals per technology and zone.
    pdf_to_svg(src["icra_ecdf"], FIG / "icra-ecdf-residuals.svg")
    # PLANS 2025, Fig. 14 (a) and (b), vector crop from p. 10 without the caption.
    pdf_clip_to_svg(src["plans_pdf"], 9, (50, 58, 572, 305), FIG / "plans-position-errors.svg")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="?", default="all", choices=["all", "photos", "figures"])
    ap.add_argument("--base", type=Path, default=ROOT.parents[1],
                    help="folder that contains hymn-localization and indoor-outdoor-localization")
    args = ap.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    src = sources(args.base)
    if args.what in ("all", "photos"):
        build_photos(src)
    if args.what in ("all", "figures"):
        build_figures(src)


if __name__ == "__main__":
    main()
