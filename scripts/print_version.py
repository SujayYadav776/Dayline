"""Print the single-source application version (pyproject.toml)."""

import tomllib
from pathlib import Path

print(
    tomllib.loads((Path(__file__).resolve().parent.parent / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]["version"]
)
