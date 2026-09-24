# Changelog

All notable changes to Dayline follow [Semantic Versioning](https://semver.org/).

## [1.3.0] — 2026-09-24

### Added
- **Natural-language quick add.** Typing "pay rent tomorrow", "gym friday",
  "ship in 3 days", "review next week" or an ISO date now appends the Obsidian
  Tasks `📅` due-date token automatically — priority `!`/`!!`/`!!!` and `#tags`
  still work. Pure `core/quickadd.py`.
- **Move-to-day.** Every task's hover actions gained a 📆 button: pick a day
  from the week card and the task moves there (the `📅` date follows, it's a
  single undoable step, and the app jumps to the new day). Replaces the old
  drag gesture, which proved unreliable under Qt's internal drag-and-drop.
- **Spring checkbox (React Bits SpringCheck port).** Checking a task now plays
  a spring-driven choreography: the accent fill swells out of the box centre
  with a gentle overshoot, the box itself bounces, the tick draws itself in two
  strokes, the label dims to 42% ink and a strike-through rule wipes across
  exactly the text's width lagging behind the fill. Pressing scales the box to
  95%. Reduced-motion (or Windows animation off) jumps straight to the end
  state. New reusable `SpringBox.qml` + Theme tokens; also fixes a latent QML
  trap — the ink token formerly named `onAccent` silently resolved to
  undefined (QML parses `onXxx:` members as signal handlers) and is now
  `accentInk`, so ticks/labels finally get true white.
- **Completion feedback.** Checking a task plays a soft ~160 ms tick. Toggle
  the sound in Settings → General ("Completion sound"); it's silent
  off-Windows and in headless runs. (The expanding ring "wave" was removed at
  the user's request — the spring checkbox carries the visual now; the strike
  rule sits at 54% of the line height for true visual center.)
- **Double-click a task → jump to its line in Obsidian.** A double-click on
  the task text deep-links into Obsidian at that exact line: if the line ends
  with a block anchor (`^id`) it opens `note#^id`; otherwise it runs an in-note
  phrase search (`obsidian://search` restricted to that day's file), which
  highlights the line. Single-click still edits inline (the editor opens after
  a 280 ms pause that a double-click cancels, so the two gestures don't
  collide).
- **Panel mode (auto-hide).** New Settings → General toggle "Auto-hide when
  unfocused": the widget dismisses to the tray the moment it loses focus, just
  like the Windows notification centre. Off by default.
- **Recurring tasks (🔁).** Completing a task whose line contains an Obsidian
  Tasks `🔁 every …` rule automatically creates the next instance in that day's
  note — strictly after the due date (never in the past), as a single undoable
  step. Supported: every day/weekday/week/month/year, every other week,
  every N days/weeks/months/years, every <weekday> (+ "every other <weekday>"),
  daily/weekly/monthly/yearly. Quick add understands typing too: "gym every
  monday" becomes `gym 📅 <next Monday> 🔁 every monday`. Pure `core/recur.py`.
- **Thin paper (translucent).** New Settings → Appearance toggle: the window
  fill goes transparent and the paper is painted at 92% opacity, so the Win11
  Mica blur faintly shows through the widget. Only offered on Mica-capable
  systems and inert while Mica is off; off by default.
- **Due reminders.** A tray toast at 09:00 reports "N due today · M overdue"
  (or "all clear"). Controlled by the Settings → General "Daily due reminder"
  toggle; existing installs are migrated to opt-in-by-default since the old
  hidden switch was never user-settable.
- **Staggered ribbon menu (React Bits StaggeredMenu port).** The hamburger on
  the bookmark ribbon now opens a full-screen staggered menu in the component's
  signature choreography, dressed in app colours: two heat-map bands
  (salmon, bookmark red) sweep in from the ribbon side with a 50 ms
  stagger, the paper panel trails them, then the uppercase nav rows
  (TODAY 01 · WEEK 02 · SETTINGS 03 · QUIT 04) rise out of clipped rows with a
  10° tilt and red superscript numbers — set in LEMON MILK (bundled
  `LEMONMILK-Regular.otf`) and settling in ~1 s.
  Closing is one synchronized fast slide-out. The ribbon and traffic lights
  float above the panel so either
  closes it (as does Escape and picking an item); reduced-motion snaps.
  Replaces the old plain slide-in drawer. New `StaggeredMenu.qml`.
- **Rounded window corners (Win11).** The frameless widget now uses the DWM
  window corner preference (`DWMWA_WINDOW_CORNER_PREFERENCE` → `ROUND`), so
  its corners match native Windows 11 windows. Applied once at startup next to
  the Mica/title-bar tweaks via `platform/dwm.set_rounded_corners`; square on
  Win10 and any failure (same graceful-degradation contract as Mica).
- **Skip Obsidian — plain-folder mode.** Onboarding step 1 gained a source
  choice: "Obsidian vault" (as before) or "Any folder". In folder mode Dayline
  stores your daily notes itself — plain markdown at
  `<folder>/Daily/YYYY-MM-DD.md` with the same `## To-Do` section, created on
  first use; no Obsidian install involved. The recovery screen carries a
  matching "Use as folder" button, double-clicking a task opens the note with
  the OS default handler instead of an `obsidian://` jump, and the choice
  persists in config (`vault_mode`; old configs default to `obsidian`).

### Fixed
- Redo of an action that created a day's note (add / move-to-day) was silently
  dropped due to an undo/redo staleness asymmetry; now it restores correctly.

### Changed
- **macOS-style title bar.** Dots sit top-right (minimise · maximise · close,
  close last); the bookmark ribbon now touches the top border with a soft drop
  shadow. The native Windows caption is gone: the window
  is frameless with a paper title strip carrying traffic-light dots (close ·
  minimize · maximize) that grey out when unfocused and show glyphs on hover.
  Dragging and resizing still use the native system handlers, so Aero Snap
  and Win+arrow tiling keep working.
- **Notification-centre placement.** Summoned from the tray, the widget docks
  to the **bottom-right of the work area** (above the taskbar) every time —
  position is no longer restored from the last drag; size still is.
- **Tray-first compact widget.** Dayline now boots to the system tray by
  default ("Start hidden in tray", Settings → General) and the window is a
  small 360×600 widget instead of a full app frame. Summon it by clicking the
  tray icon, pressing the quick-add hotkey, or launching Dayline again (a
  second launch now actually re-raises the running window — fixed). Closing
  the window hides it to the tray (unchanged default).
- **Full "paper" redesign ported from the reference mockups**: textured
  paper background, bookmark-red accent, Varela Round body type, Courier New
  typewriter headings, and a Wallpoet pixel font for the big lowercase-date
  block (bundled OFL fonts, registered at boot).
- **Navigation rebuilt to match the mockups**: red bookmark ribbon opens a
  nav drawer; header `‹ TODAY ›` steps through days; the footer is now a
  week-strip calendar (red-circle today, hairline columns, completion fill)
  with a raised tab that slides up the **Progress** panel — My-week card,
  Day streak / Tasks done cards, and a 13-week Activity heat-map.
- **Completed tasks render inline** (ticked red circle + strike-through) in
  one flat list; the "Done" and "Carried forward" sections are gone. Empty
  day shows "No tasks on this day."
- **App icon is now the exact brand logo** (window/taskbar/tray, onboarding,
  About card, drawer).

## [1.2.0] — 2026-09-20

### Added
- **Opt-in update check.** Settings → Updates has an "Auto-check (daily)"
  switch (default **off**) and a "Check now" button. When a newer GitHub
  release is found it shows a tray toast + a Settings banner with **Install
  update** (downloads the installer over https and runs it silently, force-
  closing the running app) and **Release notes** (opens the release page).
- Pure `core/updater.py` (version normalise/compare, release parsing, installer
  asset pick, once-a-day scheduling) — network and disk I/O stay in
  `platform/update_net.py` + `platform/installer.py`; the fetch runs on a
  `QThread` so the UI never blocks. https-only with a GitHub host allowlist so
  a tampered feed can't fetch a binary from an arbitrary origin.

## [1.1.1] — 2026-09-20

### Fixed
- **Frozen app crashed on launch** (`Dayline.exe` exit `0xC0000409` in
  `Qt6Core.dll`) on Windows 11 desktops. The system tray (`QSystemTrayIcon`) and
  its context menu (`QMenu`) are **QtWidgets**, but the app was bootstrapping a
  bare `QGuiApplication`; showing a widget under it makes Qt `abort()` — but only
  in a real interactive session, so the offscreen selftest/tests never caught it.
  The bootstrap now creates a **`QApplication`**. Added a regression guard test.

## [1.1.0] — 2026-09-20

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
