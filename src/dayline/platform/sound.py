"""Soft UI sounds via winmm.dll — no Qt Multimedia dependency in the bundle.

``PlaySoundW`` with ``SND_ASYNC`` fires and forgets; every failure mode
(non-Windows, missing file, old DLL quirks) is a silent no-op.
"""

from __future__ import annotations

import contextlib
import ctypes
import sys
from pathlib import Path

_SND_ASYNC = 0x00000001
_SND_FILENAME = 0x00020000


def play_wav(path: Path) -> None:
    """Play a small .wav asynchronously; never raises, never blocks the UI."""
    if sys.platform != "win32" or not path.is_file():
        return
    with contextlib.suppress(OSError, AttributeError):  # pragma: no cover - platform
        ctypes.windll.winmm.PlaySoundW(str(path), None, _SND_ASYNC | _SND_FILENAME)
