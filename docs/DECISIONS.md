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


## D-020 · Paper design system replaces shadcn port; fonts + textures bundled (v1.3.0, unreleased)
- **Context:** The user supplied two phone mockups (paper-textured home screen + pull-up "Progress" calendar panel) and asked to copy the design "pixel perfect… fonts, colours, background texture, structures, navigation". shadcn's zinc/neutral language and the segmented-tab footer had to go.
- **Decision:** Port the mockup's design system into `Theme.qml` (still the single token source): warm paper `#EDECE9` background with a generated tileable `assets/paper.png` grain (PIL, seeded), bookmark-red accent `#D64530`, white rounded cards, and three type roles — **Varela Round** (body/labels, rounded sans), **Courier New Bold** (typewriter serif headings "Progress/My week/Activity"), **Wallpoet** (pixel date digits). The two Google fonts are OFL, vendored under `assets/fonts/` and registered at boot via `app.load_bundled_fonts()` (`QFontDatabase.addApplicationFont`), with Segoe UI fallback. Spec datas bundle fonts + texture + glyph PNGs.
- **Also:** Navigation became the mockup's own: red bookmark **ribbon** = hamburger → left nav drawer; header `‹ TODAY ›` = day nav; person glyph → Settings; the footer is now a **WeekStrip** calendar (7 columns, hairline dividers, red-circle today, gray completion fill, raised `⌃` tab over the selected day that slides up the **ProgressPanel**: My-week card, Day-streak/Tasks-done cards, 13-week Activity heat-map). Ribbon/person/share are pre-rendered PNGs, not `Canvas` — Canvas paints were proven non-deterministic under `grabWindow()` (flaky screenshots). The window is now opaque paper; the Mica setting remains but is visually covered by the texture.
- **Consequence:** New pure-VM surfaces: `week_vm.strip/streak/doneToday/activity/activityMonths` (+`set_anchor`), `today_vm.dayName/dayNum/monthName`, `app_vm.selectDay`. Covered by `tests/ui/test_paper_vm.py`.


## D-021 · Completed tasks inline; Done/Carried sections removed (v1.3.0, unreleased)
- **Context:** "I don't want the done and carried forward to be displayed, instead show me the tasks that are completed with a ticked box and strike-through."
- **Decision:** `TodayViewModel` keeps its internal section lists (tests + rollover counters unchanged) but exposes one combined `tasksList = open → carried → done`; `TodayPage` renders it in a single Repeater with keyboard selection over the combined list. Completed rows draw as a red ticked circle + struck-through gray text (TaskRow already knew how); carried rows keep their `→` prefix inline. The collapsible "Done"/"Carried forward" `SectionHeader`s and the "Carried over: N" chip are gone; the empty state is the mockup's "No tasks on this day."
- **Consequence:** Section data model and note format untouched — this is purely presentation, so no migration or write-path risk.


## D-022 · Tray-first compact widget: small window, boots to tray (v1.3.0, unreleased)
- **Context:** "Better than the entire app … why not just make it a small window that stays on the system tray by default." Dayline is a glanceable daily to-do, not a full-screen app; the 440×720 window that opens on every launch was the wrong default.
- **Decision:** Default window shrunk to **360×600** (min 320×460) — a compact portrait widget that still fits the paper design (header + list + week-strip). New `Settings.start_hidden` (**default on**): once a vault is configured, `create_engine()` sets a `StartHidden` context property (guarded by `QSystemTrayIcon.isSystemTrayAvailable()`) and `Main.qml` binds `visible: !StartHidden`, so the window never flashes — the app lives in the tray and is summoned by left-clicking the tray icon, the global hotkey, or a second launch. `close_to_tray` was already on, so the X button hides to tray. A Settings → General "Start hidden in tray" toggle turns it off. On first run (no vault) `StartHidden` is false so onboarding always shows.
- **Also (bug fix):** the second-launch signal only set a `pending_show` flag that was checked once *before* the event loop — so launching again while the primary was already running (the normal case for a tray app) never surfaced the window. `AppController.show_window()` is now called directly from the single-instance callback once the controller exists.
- **Consequence:** The user's saved oversized geometry is dropped (config `window` key cleared, backed up) so the compact default takes effect. Verified live: boots to tray with a "Running in the tray" toast, tray click opens the small window, second launch re-raises it.


## D-023 · Notification-center placement: dock bottom-right on every summon (v1.3.0)
- **Context:** "I want it to open on the bottom right of the screen like the control centre or notification panel." A tray widget should appear where the tray lives, not where it was last dragged.
- **Decision:** `AppController._anchor_bottom_right()` computes `x = avail.x + avail.width - w - 12`, `y = avail.y + avail.height - h - 12` from `QScreen.availableGeometry()` (taskbar excluded; secondary-monitor origins respected) and runs inside `_show_and_raise()` — the single funnel for tray click, tray menu, and second-launch summon. `Main.qml` now restores only SIZE from saved geometry, never position; the anchor owns placement. Guarded by `except (AttributeError, TypeError)` so headless fakes/offscreen CI skip quietly. First-run onboarding still opens at the window manager's default (centred) — anchoring only applies to tray summons, matching notification-centre semantics.
- **Consequence:** Covered by `tests/ui/test_controller.py` (work-area math, monitor offset, show-then-position, quiet no-screen fallback).


## D-024 · Frameless window with macOS traffic-light title bar (v1.3.0)
- **Context:** The native Windows caption (min/max/close) clashed with the paper aesthetic; the user asked to restyle it to match the app and use the macOS three-dot design.
- **Decision:** `Qt.FramelessWindowHint` + a custom 34 px `TitleBar.qml` strip: red/amber/green dots (close → `win.close()` which still honours close-to-tray; minimise; maximise toggle), greyed when the window is inactive, glyphs on hover, faint serif "Dayline" wordmark. Window management stays NATIVE: drag uses `startSystemMove()` (keeps Aero Snap / Win+arrows), resize uses `startSystemResize()` via thin edge/corner MouseAreas (top strip starts after the dots; all disabled while maximised). The header (ribbon/nav) anchors below the strip; onboarding offsets by its height.
- **Consequence:** `apply_titlebar_theme` (DWM caption colour) becomes a no-op visually but is kept (harmless, still used if the frame is ever restored). Win11 still rounds corners + casts the shadow on the frameless window. Verified live: dots render, drag/resize/snap work, maximise respects the taskbar.
- **Follow-up:** dots moved to the TOP-RIGHT (minimise · maximise · close, close last) per user preference — Windows muscle memory with the macOS look. The bookmark ribbon was lifted to window-root (z 25, above the title strip) so it touches the very top border, and `ribbon.png` regenerated with a Gaussian-blurred drop shadow; `ribbonOverhang` clearance dropped 48→16 accordingly.


## D-025 · Quick-add power features: NL dates, drag-to-reschedule, completion feedback (v1.3.0)
- **Context:** After the paper redesign the user picked three quick wins: natural-language date parsing on add, drag-a-task-onto-a-date to reschedule, and a completion micro-animation + soft sound.
- **Decision (NL add):** new pure `core/quickadd.py` extracts ONE date phrase (today/tonight/tomorrow/next week/in N days/weekday/next weekday/ISO) → `(clean_text, due)`. `AppViewModel.addTask` re-inserts the Obsidian-Tasks `📅 YYYY-MM-DD` token *before* any trailing `!`/`!!`/`!!!` so the existing `parse_quick_syntax` still maps priority. `#tags` are untouched.
- **Decision (drag):** `TaskRow` is a `DragHandler` source (attached `Drag.keys/source` on the row — the handler reads them from its parent); each `WeekStrip` column is a `DropArea` that highlights on hover and emits `taskDropped`. `AppViewModel.rescheduleTask` calls the new `TaskEditor.move_to_day`, which copies the raw line to the target note (rewriting its `📅` to the target day) and deletes it from the source — both files captured in ONE undo op — then navigates to the target.
- **Decision (feedback):** checking an open task plays a ~160 ms sine "tick" (`assets/snap.wav`, generated by `scripts/make_sound.py`) via `platform/sound.play_wav` (winmm `PlaySoundW` SND_ASYNC — no Qt Multimedia dependency), injected into the VM as `sound_play` so it is unit-testable and a no-op off-Windows/headless. `TaskRow` pops the checkbox and pulses a red ring on the newly-done row (page tracks a one-shot `celebrateKey`). Setting `completion_sound` (default on) gates the audio; a Settings → General toggle controls it.
- **Also:** fixed a latent undo/redo asymmetry — undo writes an *empty managed doc* (never deletes a file) for a note the app created, but redo's staleness check compared against literal `b""`, so redo of any op that created a note was wrongly dropped. `_restore` now compares redo's expected state against the same empty-doc bytes.
- **Consequence:** `core/quickadd` is mypy-strict pure logic (20 tests); `move_to_day` + the undo fix are covered in `test_editor`; VM wiring (NL add, reschedule+navigate, sound on open→done only, sound-off) in `test_paper_vm`. 239 tests green.


## D-026 · Click a task → jump to its exact line in Obsidian (v1.3.0)
- **Context:** Feature-list item "click a task → jump to it in Obsidian — you already build obsidian:// URIs; extend to the exact line." Obsidian URIs cannot address a raw line number, so the line must be reached by an addressable target.
- **Decision:** two-tier deep link in pure `core/obsidian.py` (`jump_uri`): (1) if the task line ends with a block anchor the user already wrote (` ^id`), open `file=…%23%5Eid` — the officially documented heading/block form; (2) otherwise open `obsidian://search` with the query `file:"<note stem>" "<task phrase>"` — a literal phrase search restricted to that day's note, which lands on and highlights the exact line. Phrase = description with `"`→space and whitespace collapsed, capped at 80 chars; empty descriptions degrade to opening the note. Gesture split in `TaskRow`: single-click on the text opens the inline editor through a 280 ms one-shot Timer that a double-click cancels; the double-click fires the Obsidian jump (mapping flipped from the first cut at the user's request — editing is the frequent gesture, deep-linking the deliberate one); a pointing-hand cursor hints clickability. Launching is the injected `uri_open` callable on `AppViewModel` (default: `os.startfile`/xdg-open), so the VM is unit-tested without touching the OS.
- **Consequence:** 249 tests green (+10: block-ref extraction, URI encoding, cap/clean rules, VM slot incl. anchor and fallback paths). Human check: double-click lands on the right line in Obsidian; single-click opens the editor after ~280 ms and never also summons Obsidian.


## D-027 · Panel mode: auto-hide on focus loss (v1.3.0)
- **Context:** "A toggle that makes the widget dismiss when it loses focus, exactly like the notification centre."
- **Decision:** `Settings.auto_hide` (default OFF — opt-in; the app must never vanish while someone is mid-edit without asking). `AppViewModel.autoHide` exposes it to QML; `Main.qml` binds `onActiveChanged` → `win.hide()` guarded by `win.visible && App.vaultReady && App.autoHide` so onboarding and the hidden-in-tray state can't trigger it. Hide (not close) keeps the tray icon and skips the close-to-tray policy.
- **Consequence:** summoning stays via tray click / global hotkey / second launch. Live-verified: alt-tab away dismisses; tray click re-raises bottom-right.


## D-028 · Recurring tasks: 🔁 spawns the next instance into its day's note (v1.3.0)
- **Context:** "Honour Obsidian Tasks 🔁 syntax: completing '🔁 every monday' auto-creates the next instance. Huge for a daily-notes todo app."
- **Decision:** pure `core/recur.py` — `rule_of` (🔁 + text up to the next token/tag), `next_occurrence(rule, after)` (strictly after; every day/weekday/week/month/year, every other week, every N units, every <weekday> + abbreviations + "other", daily/weekly/monthly/yearly, "each" synonym; unknown rules → no repeat), month/year clamp (Jan 31→Feb 28, Feb 29→Feb 28), `next_body` (rewrite 📅, drop ✅, keep 🔁/priority/tags). `TaskEditor.toggle` was restructured to record ONE `_Op` with both file snapshots: completing a recurring task appends the next instance to the note of its due day (created if absent, same machinery as move_to-day), so a single Ctrl+Z unticks the original AND removes the spawned line. Base date = max(📅 due, note day) — completing an overdue weekly task never spawns in the past. Quick add runs `extract_recurrence` BEFORE the date-phrase parser (else "every monday" loses "monday" to the weekday rule), seeds the first 📅 with the next occurrence, and inserts `🔁 rule` before trailing bangs.
- **Consequence:** 295 tests (+~30: rule matrix incl. clamp/leap, editor spawn/undo/no-past/reopen, quickadd extraction, VM end-to-end line format). Reopen (done→open) never spawns.


## D-029 · Due reminders: 09:00 tray toast "N due today · M overdue" (v1.3.0)
- **Context:** "Tray toast for tasks due today/overdue (the notification scheduler is already built)." FR-P7's scheduler (daily QTimer → tray.notify) existed but was unreachable: no Settings UI and notifications_enabled defaulted off.
- **Decision:** `AppViewModel.due_summary()` counts OPEN tasks in today's note: no 📅 or =today → due; 📅<today → overdue (rollover already carries plain tasks forward). `_fire("morning")` composes "N due today · M overdue" / "Nothing due today — all clear." Settings → General gains a "Daily due reminder (9:00)" toggle bound to notifications_enabled (switching on backfills morning_summary_at="09:00" if empty). Defaults flip to ON + 09:00 with a v1→v2 config migration that only upgrades the never-user-settable combination (enabled=false AND morning=""), so a deliberate evening-only setup stays untouched.
- **Consequence:** toast verified live on device; migration covered by two settings tests.



## D-030 · Thin paper: 92% underlay instead of texture opacity (v1.3.0)
- **Context:** "Mica is currently hidden behind the opaque texture; a 'thin paper' mode (texture at ~92% opacity) would let the blur peek through on Win11." Diagnosis: the real blocker is the window's own `color: Theme.bg` — the paper Image is only grain (0.6/0.06 opacity). Mica can never show through a solid window fill.
- **Decision:** `Settings.thin_paper` (default OFF; Win11-only toggle). When `App.thinPaper && App.micaActive`: window `color` becomes `"transparent"` and a `Rectangle { color: Theme.bg; opacity: 0.92 }` underlay (z:-3) carries the paper colour, with the existing grain Image on top unchanged. Painting 92% of the *colour* (not the grain texture) is what produces the even "thin sheet" effect; scaling the grain's opacity instead would just fade the grain, not the paper. Off (or Win10/Mica-off) the window paints solid as before.
- **Consequence:** bindings live — toggling applies without restart. Verified on device: blur visible behind the widget over a colourful wallpaper; drag-to-reschedule re-checked in the same pass.



## D-028a · Follow-up: drag-to-reschedule uses geometry, not DropArea (v1.3.0)
- **Context:** Live testing showed the DragHandler activates (row dims/follows) but `DropArea.onEntered/onDropped` never fire — under real mouse, SendInput, and in-process events alike. Qt's internal DnD chain is unreliable in this app (frameless window + Flickable + tray widget), so the feature shipped broken: rows could be "dropped" anywhere and never rescheduled.
- **Decision:** keep the DragHandler purely as a gesture tracker (`target: null`, `dragThreshold: 14`, `grabPermissions: Qt.ExclusiveGrabber`). On active-change the row calls `beginTaskDrag`/`endTaskDrag` on the window; on release Main.qml asks `WeekStrip.dateAtPoint(scenePos)` — `mapFromScene` + `floor(x / colW)` column math — and calls the already-tested `App.rescheduleTask` when a column is hit. `setHover(dateStr)` drives the existing red column tint during the drag (via `centroid.scenePositionChanged`). Releasing anywhere else cancels cleanly.
- **Consequence:** no DnD machinery at all; the drop decision is one pure geometry function. VM/editor path unchanged (298 tests still green).



## D-031 · Move-to-day button replaces drag-to-reschedule (v1.3.0)
- **Context:** Two drag rewrites (D-028 DragHandler→DropArea, D-028a geometry drop) both failed to deliver under real input, and automated live verification was repeatedly sabotaged by foreground steals + panel-mode auto-dismiss. The user called it: "just add the move to day button instead."
- **Decision:** removed the DragHandler, centroid tracking and WeekStrip geometry helpers entirely. Each task row's hover actions gained a 📆 button that opens `MoveDayMenu` — a window-level paper card with seven day chips from `App.weekVM.strip` (today ringed red, the currently-viewed day disabled). Picking a chip calls the already-tested `App.rescheduleTask` (line moved, 📅 rewritten, navigates to the target day, single undo step). Click-outside/Esc closes. Menu is one shared instance hosted by Main.qml (`win.openMoveMenu(key, text)`), z 40 with a z 39 backdrop MouseArea.
- **Consequence:** rescheduling is now a deterministic two-click path with no gesture machinery; the drag can return later behind a setting only if it proves reliable. QML-only change (hot-synced + installer rebuilt); VM/editor untouched, 298 tests still green.



## D-032 · SpringCheck ported to QML (v1.3.0)
- **Context:** The user pasted the React Bits `<SpringCheck />` integration template (spring scalar drives fill swell + drawn tick + word dim + lagged strike wipe). Dayline is QML — the user chose "port its animation" over a React integration.
- **Decision:** new reusable `Dayline/SpringBox.qml`: one `progress` real driven by a `Behavior on progress { SpringAnimation }` (spring 3.5 / damping 0.5 / mass 0.7 → overshoots past 1 then settles), armed after first frame so app-launch and delegate rebuilds don't animate; `animateIn` (from the page's celebrate flag) replays the spring on the just-completed row. Derived visuals bind to the scalar exactly like React's `readings()`: fill `scale=max(t,0)` clipped by the box, box `scale=1+0.35·max(0,t−1)`, word alpha `1→Theme.doneOpacity`, strike rule width = `paintedWidth · clamp((t−lag)/(end−lag))` (single-line labels only; wrapped labels keep `font.strikeout`). Press scales to 0.95.
- **Two Qt traps hit and fixed:** (1) `Item.clip` does NOT clip `QtQuick.Shapes` nodes and ShapePath `strokeColor`/`fillStyle` were unreliable in this build → the tick is now two rounded Rectangles that grow in sequence (x-monotonic, so growth == draw order); (2) the Theme token formerly named `onAccent` — QML parses `onXxx:` members as signal handlers, so the property silently never existed and every read site got undefined (black Rectangles). Renamed to `accentInk` across 8 files.
- **Consequence:** 298 tests green (QML-only), offscreen renders prove off=clean ring / on=red+white tick. The celebration pulse ring + sound are unchanged.

### D-032 addendum (same day, user feedback)
- Removed the celebration pulse ring ("wave") entirely — the spring checkbox is the completion visual now; `celebrate` only replays SpringBox's animateIn and clears the page flag. Strike rule moved to `y = height * 0.54` (46% read high since ascenders outweigh descenders; 54% matches where `font.strikeout` crosses).



## D-033 · StaggeredMenu ported to QML for the ribbon (v1.3.0)
- **Context:** The user supplied a simplified StaggeredMenu-QML zip ("use this for the menu button on the ribbon"), then pasted the real React Bits GSAP+CSS source and asked for a redo against it. The component: colour pre-layers sweep in with a stagger, a panel trails them, uppercase labels rise out of clipped rows with a 10° tilt, superscript numbers fade behind them, and the exit is one synchronized fast slide (≤1024px the panel is full width).
- **Decision:** new `Dayline/StaggeredMenu.qml` matching the original choreography in Dayline's paper palette. Pre-layers = the app's own activity heat-map ramp (`Theme.heatColor(2)` salmon leading + `Theme.heatColor(4)` bookmark red trailing; the first cut used three bands and the user asked for fewer + a snappier timeline → durations trimmed to ~40% of the GSAP originals: layers 380 ms/50 ms stagger, panel 460 ms/+160 ms, rows 600 ms/60 ms stagger, exit 240 ms) so the colour panels read as app colours. Menu labels are set in **LEMON MILK** (the user's own `D:\FONTS\fontss\LEMONMILK-Regular.otf`, family name "LEMON MILK", bundled into `assets/fonts/` and exposed as `Theme.menuFamily`; it ships Regular-only so no synthetic bold, and its wide caps replace the negative tracking — an earlier Google "Lemon" cut was swapped out at the user's request). Because the file is an OTF, `load_bundled_fonts()` now registers `*.otf` alongside `*.ttf`. Full-width panel, no scrim (the original has none). The bookmark ribbon replaces the built-in Menu/Close toggle (z 25 > menu z 22) and toggles; the title bar was raised to z 23 so traffic lights stay clickable above the panel; Escape and item picks also close. `win.drawerOpen` remains the single source of truth — the component only emits `dismiss()`/`itemChosen(id)`, never assigns `opened` (that would kill the host binding). Socials + logo header dropped (no Dayline equivalent); the old plain drawer was deleted.
- **Three QML traps hit:** (1) *stale Behavior bindings* — a direction-aware `Behavior on x` whose PauseAnimation/NumberAnimation durations bind to `root.opened` reads the OLD value when triggered, so the exit ran with entrance timings (caught by offscreen frame probes; the zip's declarative-Behavior approach was replaced with explicit open/close animations started from an `on<sync>Changed` handler); (2) *required-property context loss* — a delegate that declares any `required property` does NOT get implicit `modelData` injection in this Qt build; the layer delegate declared only `index` and used bare `modelData`, which resolved to undefined → all three panels rendered silently as white Rectangles (no console error). Fixed by declaring `required property var modelData`; (3) *Repeater delegates are visual children only* — they appear in `childItems()`, not in the QObject `children()` tree, so PySide6 `findChildren("menuLayer")` returns 0 even when the items exist and animate. QA probes must scan `childItems()`.
- **Consequence:** 298 tests green (QML-only). Offscreen frame probes capture the whole timeline (bands → sweep → rising rows → open → synchronized exit → closed) in both themes; live check confirmed ribbon-open, item navigation and auto-close. Menu root gates `visible` on `opened || panel.exiting` so closed-state buttons don't pollute the accessibility/UIA tree.



## D-034 · Win11 rounded corners via DWM corner preference (v1.3.0)
- **Context:** "Round the corners of the app to match the Windows 11 theme." The widget is frameless (`Qt.FramelessWindowHint`), so it never inherits the OS rounder that normal windows get — its paper background runs square into the corner pixels.
- **Decision:** `platform/dwm.set_rounded_corners(hwnd)` sets `DWMWA_WINDOW_CORNER_PREFERENCE` (33) → `DWMWCP_ROUND` (2), the same API every Win11 app uses; DWM clips the window region itself, so no per-corner alpha painting is needed and it composes correctly with the Mica backdrop and the staggered menu overlay. Called once from `app.py` startup next to `apply_titlebar_theme`/`apply_backdrop` (a static preference — no change hook). Gated by `supports_system_backdrop()` (build ≥ 22000) and wrapped in the standard try/except → returns False and the window simply stays square on Win10 or any failure.
- **Consequence:** 300 tests green (+2: no-op without hwnd, graceful False off Win11). Requires a full PyInstaller rebuild (Python-side change) — this rebuild also carries the OTF font-loader fix into the frozen build.



## D-035 · Plain-folder mode: skip Obsidian, Dayline stores the notes (v1.3.0)
- **Context:** "On the onboarding also add the option to skip the obsidian vault and use any folder on their computer and store the data." Dayline's storage was already plain markdown (`Daily/YYYY-MM-DD.md` + `## To-Do`), so the Obsidian coupling is really just *discovery* (obsidian.json, daily-notes.json) and *deep links* (obsidian://).
- **Decision:** new `Settings.vault_mode` ∈ {`obsidian`, `folder`}, default `obsidian`; old configs lack the key and `_coerce` falls back to the default, so no schema bump or migration is needed (validate clamps unknown values). Onboarding step 1 gets two mode chips; folder mode hides the detected-vault list, and `finish()` calls the new `AppViewModel.selectFolder(path)` slot — validate dir, set mode/path plus Dayline's own defaults (`Daily`, `YYYY-MM-DD`), persist, start. The recovery screen gains a "Use as folder" button beside "Use vault". Obsidian-specific affordances branch on the mode: `openTaskInObsidian`/`openInObsidian` open the day's file via the injected `file_open` (OS default handler, same pattern as `uri_open`) instead of building `obsidian://` URIs. The Store already creates missing notes/folders, so no writer changes.
- **Consequence:** 308 tests (+8: settings default/roundtrip/missing-key/clamp; VM selectFolder persist+build, note creation, file-open jump, mode reset by selectVault). Full PyInstaller rebuild required (core+VM changes). QML verified on the real windows platform — the offscreen matcher renders everything in LEMON MILK (all-caps artifact), another reminder that font checks need `QT_QPA_PLATFORM=windows`.
