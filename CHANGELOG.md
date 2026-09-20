# Changelog

All notable changes to Dayline follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### UI
- Windows 11 **Mica** translucent backdrop, on by default. Gated to build
  22000+ via `DWMWA_SYSTEMBACKDROP_TYPE`; the window requests an alpha surface
  and tints `Theme.bg` at 80% opacity so the OS blur shows through the header,
  list gaps and margins while cards stay solid. Falls back to the plain opaque
  theme off Win11 (no `DwmExtendFrameIntoClientArea`, so no black-glass risk).
- Settings → Appearance gains a "Mica backdrop" toggle (shown only where the OS
  supports it). Persisted as `Settings.mica` (default `true`).

## [1.0.0] — 2026-09-20

First production release. A Windows desktop to-do app that uses an Obsidian
vault (daily notes) as its database.

### Core
- Surgical Markdown parser/serializer: unmodified daily notes round-trip
  byte-identically (BOM, CRLF/LF/CR, trailing newline, tabs, front-matter).
- `Store.mutate`: per-path lock, fresh read-modify-write, atomic temp+rename,
  re-stat race guard (≤3 loops), `PermissionError` backoff (50–800 ms),
  own-write suppression, and rolling backups (`%LOCALAPPDATA%\Dayline\backups`).
- Normative rollover (PRD §5.5): idempotent, no task loss, order-preserving,
  metadata/priority preserved, cancelled/unknown never carried, subtasks move
  with their parent. Property-tested (≥320 generated cases; round-trip 2×1000).
- Moment.js date-format subset with unsupported-token detection + fallback.
- Obsidian vault + daily-notes config discovery; `obsidian://open` URIs.
- Versioned, migrated, atomically-saved JSON settings.
- Logical day ("day starts at"), DST-safe; sleep/wake detection.

### UI (PySide6 / QML, Basic style, Theme-singleton tokens)
- Today: progress ring, To do / Done / Carried sections, add bar, inline edit,
  priority cycling, delete, keyboard-first (Space/F2/Delete/1-2-3-0/Alt+arrows).
- Week: per-day bars + totals, click-to-open, month heat-map.
- Settings (live-apply) and a 3-step first-run Onboarding wizard.
- Light/dark themes matching Windows; both verified via rendered screenshots.

### Windows integration
- System tray + menu, close-to-tray, single instance, autostart (HKCU Run),
  global quick-add hotkey (RegisterHotKey) + frameless quick-add popup,
  optional notifications, immersive dark title bar (DWM).

### Packaging & quality
- PyInstaller onedir `Dayline.exe` with version resource + icon; Inno Setup
  per-user installer that never touches the vault or user data.
- `--selftest` frozen smoke in CI; GitHub Actions on `windows-latest`.
- 150 tests (unit + property + VM + integration), ruff + mypy (strict on core) clean.
- Global crash handler with a "Open logs folder" dialog; INFO logs never
  contain task text.

### Known limitations (v1)
- Recurrence markers (`🔁`) are preserved but not executed.
- No code-signing certificate → Windows SmartScreen "unknown publisher"
  warning on first run (personal distribution).
