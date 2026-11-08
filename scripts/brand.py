#!/usr/bin/env python3
"""Render the brand PNGs from the SVG masters in assets/brand/.

Needs rsvg-convert (librsvg) and magick (ImageMagick) on PATH.
Run after editing a master: python3 scripts/brand.py
"""

import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/brand"
BRAND = ROOT / "custom_components/iphone_alarms_sync/brand"

# master, output, width, height
TARGETS = [
    ("icon.svg", BRAND / "icon.png", 256, 256),
    ("icon.svg", BRAND / "icon@2x.png", 512, 512),
    ("banner.svg", ROOT / "assets/social-preview.png", 1280, 640),
]


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", head[16:24])


def main() -> None:
    for master, out, width, height in TARGETS:
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "rsvg-convert",
                "-w",
                str(width),
                "-h",
                str(height),
                "-o",
                str(out),
                str(SRC / master),
            ],
            check=True,
        )
        # Brand spec: compressed, interlaced, no metadata.
        subprocess.run(
            ["magick", str(out), "-strip", "-interlace", "PNG", str(out)], check=True
        )
        assert png_size(out) == (width, height), (
            f"{out}: {png_size(out)} != {(width, height)}"
        )
        print(f"{out.relative_to(ROOT)}  {width}x{height}")


if __name__ == "__main__":
    main()
