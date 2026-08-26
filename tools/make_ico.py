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


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    img.save(
        DST,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
    )
    print(f"written: {DST} ({DST.stat().st_size} bytes, sizes={SIZES})")


if __name__ == "__main__":
    main()
