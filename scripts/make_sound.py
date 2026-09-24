"""Synthesize the soft completion tick (assets/snap.wav).

Run:  uv run python scripts/make_sound.py
A 160 ms downward sine pluck (880→~640 Hz) with fast exponential decay,
4 ms attack (no click) and low amplitude — quiet, warm, non-annoying.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "dayline" / "ui" / "assets" / "snap.wav"
SR = 22050
DUR = 0.16


def main() -> None:
    frames = bytearray()
    for i in range(int(SR * DUR)):
        t = i / SR
        env = math.exp(-t * 26)
        fade_in = min(1.0, t / 0.004)
        f = 880 - 240 * t
        s = math.sin(2 * math.pi * f * t) * 0.75 + math.sin(2 * math.pi * f * 2 * t) * 0.25
        v = s * env * fade_in * 0.20
        frames += struct.pack("<h", max(-32767, min(32767, int(v * 32767))))
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(f"sound written to {OUT}")


if __name__ == "__main__":
    main()
