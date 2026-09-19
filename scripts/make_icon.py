"""Generate the multi-size app icon (placeholder until the M2 design pass).

Run:  uv run python scripts/make_icon.py
Writes src/dayline/ui/assets/app.ico and app.png (256 px).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "dayline" / "ui" / "assets"
SIZE = 256
ACCENT = (79, 107, 237, 255)  # Theme light accent
WHITE = (255, 255, 255, 255)
DIM = (255, 255, 255, 150)


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    r: int,
    fill: tuple[int, int, int, int],
) -> None:
    draw.rounded_rectangle(box, radius=r, fill=fill)


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 16
    radius = size // 5
    _rounded_rect(d, (pad, pad, size - pad, size - pad), radius, ACCENT)

    # "day line": three task rows — two open circles, one checked
    row_y = [size // 4 + size // 14, size // 2, 3 * size // 4 - size // 14]
    dot_r = size // 18
    x0 = size // 5
    x1 = size - size // 4
    lw = max(2, size // 32)
    for i, y in enumerate(row_y):
        d.ellipse(
            (x0 - dot_r, y - dot_r, x0 + dot_r, y + dot_r),
            outline=WHITE,
            width=lw,
        )
        if i == 2:  # done row: filled + check
            d.ellipse((x0 - dot_r, y - dot_r, x0 + dot_r, y + dot_r), fill=WHITE)
            k = dot_r / 2.4
            d.line(
                (x0 - k, y, x0 - k / 4, y + k, x0 + k, y - k * 0.9),
                fill=ACCENT,
                width=max(2, size // 40),
            )
        d.line(
            (x0 + dot_r * 2.4, y, x1 if i else int(x1 * 0.78), y),
            fill=WHITE if i < 2 else DIM,
            width=lw,
        )
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = render(SIZE)
    base.save(OUT_DIR / "app.png")
    base.save(
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
