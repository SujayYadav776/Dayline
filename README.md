# Dayline

A Windows desktop to-do app that uses an **Obsidian vault as its database** —
daily notes stay plain Markdown checkboxes; Dayline adds a focused Today view,
a live progress ring, automatic carry-over of unfinished tasks, a weekly
overview with a month heat-map, a system tray, and a global quick-add hotkey.

**Status:** v1.0.0 — feature-complete per the PRD (P0 + P1).

Design principles: never corrupt a note (surgical, atomic, byte-identical
round-trips), zero telemetry, and a calm keyboard-first UI that follows the
Windows light/dark theme.

## Requirements

- Windows 10 22H2 / Windows 11, x64
- [uv](https://docs.astral.sh/uv/) (Python 3.12 is provisioned automatically)

## Development

```sh
uv sync                                  # venv (Python 3.12) + pinned deps
uv run python -m dayline                 # run the app
uv run python -m dayline --minimized     # start hidden to tray
uv run python -m dayline --selftest      # boot UI, verify QML, exit 0/1

uv run pytest -q                         # 150 tests (Qt runs offscreen)
uv run ruff check . && uv run ruff format --check .
uv run mypy                              # strict on core/
```

Visual QA (renders both themes + every state to `dist/screenshots-real`):

```sh
uv run python scripts/screenshot_pages.py
```

## Build the executable

```sh
uv run python scripts/make_icon.py                       # regenerate app.ico/app.png
uv run pyinstaller packaging/dayline.spec --noconfirm     # -> dist/Dayline/Dayline.exe
dist\Dayline\Dayline.exe --selftest                       # frozen smoke (exit 0)
```

## Installer (Inno Setup)

```sh
winget install JRSoftware.InnoSetup
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 packaging\installer.iss
# -> dist\installer\Dayline-Setup-1.0.0.exe  (per-user, no admin; never deletes user data)
```

## CI

`.github/workflows/build.yml` runs on `windows-latest`: lint → type-check →
tests → frozen build + `--selftest` → installer artifact; on a `v*` tag it
attaches the installer to a GitHub Release.

## Layout

```
src/dayline/
  core/       pure Python, no Qt: model, parser, serializer, store, rollover,
              stats, moment_format, obsidian, settings, clock, editor, watcher
  platform/   Windows adapters behind interfaces: autostart, single_instance,
              hotkey, tray, dwm, system_theme, paths (fakes for tests)
  ui/         viewmodels (app/today/week/settings), QML (Theme-driven), sync, crash
```

Dependency rule: `core ← viewmodels ← qml`; `platform` is injected; `core`
imports nothing from the other layers. See `docs/ARCHITECTURE.md`,
`docs/DECISIONS.md`, `docs/QA.md`, and `CHANGELOG.md`.
