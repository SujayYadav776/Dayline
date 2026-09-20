"""Launch the downloaded Inno Setup installer silently (Windows).

Started detached so it keeps running after Dayline quits; the installer is
configured with ``CloseApplications=force`` so it closes a still-running
instance before replacing files. Returns True if the process was spawned."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ARGS = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART")


def launch_setup_exe(path: str | Path) -> bool:
    if sys.platform != "win32":  # pragma: no cover - non-Windows dev
        return False
    flags = 0
    for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        flags |= getattr(subprocess, name, 0)
    try:
        subprocess.Popen([str(path), *_ARGS], creationflags=flags, close_fds=True)
        return True
    except (OSError, ValueError):
        return False
