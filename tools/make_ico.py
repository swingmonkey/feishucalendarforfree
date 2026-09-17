#!/usr/bin/env python3
"""Generate assets/icon.ico from assets/icon_256x256.png.

Produces a standard Windows multi-resolution icon
(16/24/32/48/64/128/256).  Requires Pillow; run once and commit the
result so packagers and CI do not need Pillow:

    python tools/make_ico.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "icon.iconset" / "icon_256x256.png"
DST = ROOT / "assets" / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]
ALPHA_THRESHOLD = 64
CONTENT_SCALE = 0.92


def _trimmed(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A").point(
        lambda value: 255 if value > ALPHA_THRESHOLD else 0
    )
    bbox = alpha.getbbox()
    return img.crop(bbox) if bbox else img


def _fit_square(img: Image.Image, size: int) -> Image.Image:
    inner = max(1, round(size * CONTENT_SCALE))
    scale = min(inner / img.width, inner / img.height)
    fitted_size = (
        max(1, round(img.width * scale)),
        max(1, round(img.height * scale)),
    )
    fitted = img.resize(fitted_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(
        fitted,
        ((size - fitted.width) // 2, (size - fitted.height) // 2),
    )
    return canvas


def main() -> None:
    img = _fit_square(_trimmed(Image.open(SRC).convert("RGBA")), max(SIZES))
    img.save(
        DST,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
    )
    print(f"written: {DST} ({DST.stat().st_size} bytes, sizes={SIZES})")


if __name__ == "__main__":
    main()
