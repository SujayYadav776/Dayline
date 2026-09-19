# Dayline

A Windows desktop to-do app that uses an **Obsidian vault as its database** —
daily notes stay plain Markdown; Dayline adds a focused Today view, a live
progress ring, automatic carry-over of unfinished tasks, a weekly overview,
tray presence and a global quick-add hotkey.

Status: under construction (M0 — foundations & packaging spike). See `PRD`
spec in `docs/` milestones and `docs/ARCHITECTURE.md`.

## Development

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is provisioned automatically.

```sh
uv sync                          # create .venv (Python 3.12) + pinned deps
uv run python -m dayline         # run the app
uv run pytest -q                 # tests (Qt runs offscreen)
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## Build & package

```sh
uv run python scripts/make_icon.py                 # regenerate app.ico/app.png
uv run pyinstaller packaging/dayline.spec --noconfirm
dist\Dayline\Dayline.exe --selftest                # frozen smoke test (exit 0)

# Installer (needs Inno Setup 6: `winget install JRSoftware.InnoSetup`)
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" /DAppVersion=0.0.1 packaging\installer.iss
```

## Layout

`src/dayline/core` (pure Python, no Qt) → `ui/viewmodels` → `ui/qml`;
Windows adapters in `platform/` behind interfaces. Docs: `DECISIONS.md`,
`ARCHITECTURE.md`, `QA.md`.
