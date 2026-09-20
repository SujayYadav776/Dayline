# Decision Log (ADR-lite)

Format: Context → Options → Decision → Consequence. Every deviation from the
PRD and every resolved ambiguity lands here.

## D-001 · Python 3.12 via uv on a 3.13 machine
- **Context:** PRD pins Python 3.12; the build machine has 3.13 (system) and no 3.12.
- **Options:** (a) build on 3.13 and log a deviation, (b) provision 3.12 exactly via `uv python install 3.12`.
- **Decision:** (b). Repo carries `.python-version = 3.12`; `requires-python = "==3.12.*"`.
- **Consequence:** Toolchain drift impossible; uv download adds ~10 s once per machine.

## D-002 · PySide6 pinned to 6.9.3 (not newest 6.11.2)
- **Context:** PRD requires an exact pin; newest Qt is riskier with PyInstaller hooks.
- **Options:** 6.11.2 (bleeding edge) vs 6.9.3 (settled LTS-ish line, mature packaging support).
- **Decision:** 6.9.3.
- **Consequence:** Known-good QML plugin collection in frozen builds; re-evaluate bump at M7.

## D-003 · QML module directory layout (`ui/qml/Dayline/`)
- **Context:** `Theme.qml` must be a real QML singleton (PRD §2 design tokens). Module lookup requires a directory whose name matches the module, reachable from an import path.
- **Options:** (a) `setContextProperty` hack (not a Theme.qml singleton — rejected), (b) C++-style resource registration, (c) put types in `ui/qml/Dayline/` with a `qmldir`, load `ui/qml/Main.qml` by file URL with `addImportPath(ui/qml)`.
- **Decision:** (c). Minor deviation from PRD §6.2 tree (extra `Dayline/` folder under `qml/`).
- **Consequence:** `import Dayline` resolves identically in dev and frozen builds; `Main.qml` stays outside the module so the module never self-imports.

## D-004 · `dayline.platform` package name
- **Context:** PRD §6.2 names the adapter layer `platform/`, colliding in name only with the stdlib `platform` module.
- **Decision:** Keep it: absolute imports mean `import platform` still hits the stdlib; `dayline.platform` is unambiguous.
- **Consequence:** No shadowing; reviewers should not do relative imports of the stdlib module inside the package.

## D-005 · Version resource generated at build time
- **Context:** Single source of truth for version is `pyproject.toml` (PRD §7); PyInstaller wants a `version_info.txt`, Inno wants `/DAppVersion`.
- **Decision:** `packaging/dayline.spec` reads pyproject and generates the version resource into the (ignored) `packaging/` build area; CI passes the version to ISCC explicitly.
- **Consequence:** Zero version duplication; `build/` noise never committed.

## D-006 · Icon is a generated placeholder until the M2 design pass
- **Context:** PRD wants "own icon"; design polish is an M2 UI concern but packaging needs an `.ico` now.
- **Decision:** `scripts/make_icon.py` (Pillow, dev-only) renders the accent "day line" glyph into `app.ico`/`app.png`, committed as generated assets.
- **Consequence:** Real multi-size icon from day one; restyled in M2/M5 without pipeline changes.

## D-007 · CI frozen-build smoke uses `QT_QPA_PLATFORM=offscreen`
- **Context:** GitHub `windows-latest` runners have no interactive session; the windowed exe must still prove QML boot.
- **Decision:** CI sets offscreen for `--selftest`; local verification additionally runs with a real window.
- **Consequence:** Packaging risk (QML plugin collection) is covered in CI without display hacks.

## D-008 · GitHub remote + Release creation deferred to M7
- **Context:** PRD targets GitHub Actions and tag-triggered releases; nothing requires the remote repo during M0–M6.
- **Decision:** Local git repo now (conventional commits); create/push the remote at M7 with the v1.0.0 tag.
- **Consequence:** CI workflow is committed and correct from M0 but first real green run happens at M7 unless the user wants the remote earlier.

## D-009 · Priority dark-theme colors
- **Context:** PRD §4.2 lists priority light colors and "slightly lighter equivalents (AA on surface)" for dark.
- **Decision:** Material-400 values `#EF5350` / `#FFB74D` / `#64B5F6`.
- **Consequence:** AA contrast on `#1F2024`/`#26282D` surfaces holds (verified visually in M2 screenshot pass).

## D-010 · Rollover writes: copies before source marks (M1)
- **Context:** PRD §5.5 lists marking inline while scanning; a crash between phases must never hide a task.
- **Decision:** two-phase write — append copies to today FIRST, then mark sources `>`. A crash in between can duplicate (dedupe suppresses next run), never lose.
- **Consequence:** FR-R1..R8 hold; idempotence proven by 320-case property test.

## D-011 · Moment unsupported-token detection = token letters only (M1)
- **Context:** §5.4 wants warnings for unsupported tokens, but Obsidian formats also contain plain words ("Week of").
- **Decision:** flag letters that are real Moment format tokens outside []-escapes (GgQqYwWEaAHkKmsSXZod); non-token letters pass through as literals, exactly like Moment itself does. `[literal stays]`-style escaping remains the correct way to hold token letters verbatim.
- **Consequence:** `gggg-[W]ww`, `HH:mm` warn; `YYYY年MM月DD日` works; UI shows warning + `YYYY-MM-DD` fallback per FR-O3.

## D-012 · Dirty-line re-render normalizes `]`+space (M1)
- **Context:** a malformed source line like `- [ ]text` (no space) parses; Obsidian only renders checkboxes with `] `.
- **Decision:** when a line is (re-)serialized because it was edited, gap defaults to a single space; untouched lines are never re-rendered, so user bytes survive verbatim.
- **Consequence:** edits silently fix malformed checkboxes instead of writing broken Markdown; round-trip of unmodified notes is unaffected (property-tested).

## D-013 · Today sections exposed as row-dict lists, not a QAbstractListModel (M2)
- **Context:** PRD §6.4 suggests "QML lists use models with stable roles". A `QAbstractListModel` subclass was built first. PySide6 cannot register a model-typed `Property` (metaobject rejects `QAbstractListModel*`), and a custom-component Repeater delegate with `required property` role bindings silently created 0 delegates (only a plain-`Item` delegate worked), costing significant debugging.
- **Options:** (a) context-property the model + ListView (heavy nesting in a scroll page); (b) keep model, use inline `Item` delegates (loses the reusable TaskRow component); (c) expose each section as a plain `list[dict]` via a pure `task_to_row` mapper and bind `Repeater { model: vm.todoList; delegate: TaskRow { required property var modelData } }`.
- **Decision:** (c). Row dicts are rebuilt and the `changed` signal re-fires on every reload; lists are small (≤ a few hundred).
- **Consequence:** Reliable rendering, a genuinely reusable TaskRow, and a Qt-free `task_model.task_to_row` mapper that is unit-testable. A real `QAbstractItemModel` can be reintroduced in M4 for the Week page's larger virtualised grid if profiling ever demands it. Verified by offscreen renders in both themes (scripts/screenshot_pages.py).

## D-014 · Screenshot QA uses QWindow.grabWindow on the real platform (M2)
- **Context:** Offscreen platform renders layout but lacks system fonts (tofu glyphs), so it can't validate typography/colour.
- **Decision:** `scripts/screenshot_pages.py` renders via `QT_QPA_PLATFORM=windows` + `win.grabWindow()` for visual QA; CI keeps offscreen for the functional selftest.
- **Consequence:** Both themes are visually verified on a real Windows box; CI stays headless.


## D-015 · Snapshot-based undo with a stale-write guard (M3)
- **Context:** FR-T6 wants session undo/redo of add/edit/complete/delete/reorder/priority. Surgical edits make per-field inverses fiddly, and blind byte-restore could clobber a concurrent Obsidian edit.
- **Decision:** each action records (path, existed_before, before_bytes, after_bytes). Undo/redo restores bytes only when the file currently equals the expected side; a mismatch (external edit since) makes the step a no-op rather than a clobber. Undoing a note the app *created* restores an empty managed section (never deletes a file).
- **Consequence:** correct, safe, ≤100-step history; verified by test_editor (undo/redo, created-note, stale-skip) and test_actions (no self-reload loop).


## D-016 · Windows integrations degrade gracefully off a real desktop (M5)
- **Context:** the frozen `--selftest` and CI run headless (offscreen). Calling `QSystemTrayIcon.show()` or DWM there segfaulted.
- **Decision:** guard `tray.show()` behind `QSystemTrayIcon.isSystemTrayAvailable()`; only install the native hotkey filter on `win32`; `set_dark_titlebar` already returns False off-Windows. The selftest path skips `_integrate_windows` entirely.
- **Consequence:** headless/CI boots clean; tray/hotkey/DWM/autostart are exercised by unit tests with fakes and a headless Windows smoke (single-instance acquire + real RegisterHotKey confirmed). Final tray icon, hotkey popup, autostart-after-reboot, and dark title bar need an interactive Windows session — documented in QA.md as human steps.
- **Also:** `ctypes.wintypes` must be imported explicitly (`import ctypes.wintypes`); `ctypes.windll` alone doesn't pull it in, which crashed the native event filter on every message.


## D-017 · Mica backdrop, default-on, gated to Windows 11 (polish)
- **Context:** A polish request wants the Win11 translucent "Mica" material behind the app. DWM only exposes it on Windows 11 (build 22000+), and it is only visible where the client area is actually translucent — an opaque Qt window would hide it, and extending glass into an opaque surface risks black regions.
- **Decision:** `platform/dwm.supports_system_backdrop()` gates on the OS build number (a pure, headless-safe fact: 0 off-Windows → False). `set_mica_backdrop()` sets `DWMWA_SYSTEMBACKDROP_TYPE = DWMSBT_MAINWINDOW` (or `DWMSBT_NONE` when off). On Win11 the bootstrap requests an 8-bit **alpha** default surface, and `Main.qml` tints the window `Theme.bg` at **0.80** opacity only while `App.micaActive` is true. Pages are transparent `Item`s and only cards/rows paint solid `Theme.surface`, so Mica shows through the header, list gaps and margins while content stays legible. No `DwmExtendFrameIntoClientArea` (avoids the black-glass pitfall).
- **Also:** `AppViewModel.micaActive = settings.mica AND OS-support` (a `mica_probe` is injected for tests); `micaSupported` alone drives whether the Settings toggle appears, so Win10 users never see a dead switch. Both fall back to the plain opaque theme off Win11 — verified by offscreen tests (probe fakes + build-parametrised dwm gate) and `--selftest` on CI (build < 22000 → no translucency, no black). The see-through look itself is an interactive-Windows human check in QA.md.


## D-018 · Boot as QApplication, not QGuiApplication (v1.1.1 crash fix)
- **Context:** The v1.1.0 frozen exe crashed on real Win11 desktops — `Application Error 1000`, faulting module `Qt6Core.dll`, exception `0xC0000409` (a Qt `__fastfail`, code 7 = FATAL_APP_EXIT). The offscreen selftest and unit tests never reproduced it. A frozen build instrumented with flushed trace markers pinpointed the abort to `tray.show()`.
- **Decision:** `Tray` uses `QSystemTrayIcon` + `QMenu` — both **QtWidgets** — which require a `QApplication`. `app.main()` had been creating a `QGuiApplication`; showing a widget under that is illegal and Qt aborts, but only with the real `windows` platform plugin (offscreen stubs the tray, and `conftest` already used `QApplication`, so nothing caught it). `main()` now constructs `QApplication` (a strict superset of `QGuiApplication`, fully compatible with `QQmlApplicationEngine`).
- **Consequence:** Verified: a frozen console build booted through `tray.show()`/hotkey/DWM/backdrop and stayed alive on the real desktop (previously aborted at the same step). Added a static regression guard (`test_shell_smoke`) asserting `main()` uses `QApplication(` and never `QGuiApplication(`. Lesson logged to QA.md: the tray/hotkey/DWM paths must be smoke-tested in a *real* interactive Windows session, not just offscreen.


## D-019 · Opt-in update check via the public GitHub Releases API (v1.2.0)
- **Context:** The user asked whether pushing a new release notifies installed copies; it didn't. Dayline's default stance is no telemetry, so any check must be a deliberate, user-consented exception. The repo was private and a distributed exe must never embed a token, so a public source of "latest version" is required.
- **Decision:** Make the repo **public** and read `https://api.github.com/repos/<owner>/<Dayline>/releases/latest` (no auth; ~60 req/hr/IP is ample for an opt-in once-a-day check). Feature is **opt-in, default off** (`Settings.update_check_enabled`) with a manual "Check now" always available, plus a daily automatic check throttled by `Settings.update_last_check` (ISO, naive local). Layering stays pure-first: `core/updater` (version normalise/compare, release→`UpdateInfo`, installer-asset pick, `should_check`) does no I/O; `platform/update_net` does https with a **scheme+host allowlist** (github.com family only) so a tampered feed can't fetch a binary from an arbitrary origin; `platform/installer` launches the downloaded `Dayline-Setup-<ver>.exe` with `/VERYSILENT` detached, and the `.iss` gained `CloseApplications=force` so it replaces files while the old instance is force-closed. `ui/update_service.UpdateService` runs the fetch on a `QThread` and marshals results via queued Qt signals so the UI never blocks; only the GUI thread touches settings/QML state.
- **Consequence:** A found update surfaces as a tray toast + a Settings banner with Install/Release-notes; nothing downloads or installs without a click. Covered by `core` unit tests (parse/compare/asset/schedule + error propagation), a host-allowlist test, and threaded VM tests with a fake fetcher. The one real-network path (live GitHub call + silent upgrade over a running instance) is an interactive-Windows human check in QA.md.
