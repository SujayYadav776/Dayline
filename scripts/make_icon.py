"""Regenerate app.png / app.ico from the exact brand logo artwork.

Run:  uv run python scripts/make_icon.py
Reads src/dayline/ui/assets/logo_src.png (the removebg logo — used EXACTLY:
no crop of the artwork itself and no corner mask; only the fully-transparent
border is trimmed and a small uniform margin is added so the mark fills the
icon canvas). Writes app.png (512) and app.ico (16..256).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "dayline" / "ui" / "assets"
SRC = OUT_DIR / "logo_src.png"
PAD_FRAC = 0.045  # breathing room around the trimmed artwork


def build(size: int = 512) -> Image.Image:
    logo = Image.open(SRC).convert("RGBA")
    bbox = logo.getbbox()  # trim only the transparent border
    crop = logo.crop(bbox)
    w, h = crop.size
    side = max(w, h)
    pad = int(side * PAD_FRAC)
    canvas = side + 2 * pad
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(crop, (pad + (canvas - 2 * pad - w) // 2, pad + (canvas - 2 * pad - h) // 2))
    return out.resize((size, size), Image.LANCZOS)


def main() -> None:
    app = build(512)
    app.save(OUT_DIR / "app.png")
    app.save(
        OUT_DIR / "app.ico",
        sizes=[
            (16, 16),
            (20, 20),
            (24, 24),
            (32, 32),
            (40, 40),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )
    print(f"icon written to {OUT_DIR}")


if __name__ == "__main__":
    main()
