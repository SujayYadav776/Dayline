# Architecture

## Layers (dependency rule: core ← viewmodels ← qml; `platform` injected; core imports nothing from other layers)

```
src/dayline/
├─ core/        pure Python, no Qt: model, parser, serializer, store, rollover,
│               stats, moment_format, obsidian discovery, settings, clock
├─ platform/    Windows adapters behind interfaces (autostart, single instance,
│               hotkey, notifications, tray, dwm, paths); fakes for tests
├─ ui/viewmodels/  QObject bridges (app, today); task_model.py is a pure
│                  Task→row-dict mapper (D-013); week/settings added in M4
├─ ui/qml/      presentation only; Theme singleton in Dayline/qmldir (D-003)
└─ app.py       bootstrap: args (--selftest/--minimized), engine, wiring
```

- **Surgical editing:** the parser keeps raw lines; the serializer re-emits only
  task lines that changed. Unmodified notes round-trip byte-identically
  (BOM, CRLF/LF, trailing newline, tabs/spaces, front-matter).
- **Store.mutate(date, fn):** per-path lock → fresh read+stat → fn on fresh
  parse → serialize → temp file in same dir → flush+fsync → re-stat guard
  (retry ≤ 3) → `os.replace` → backoff on `PermissionError`
  (50/100/200/400/800 ms) → remember `(mtime_ns, size, sha1)` to suppress our
  own watcher event. Rolling backups under `%LOCALAPPDATA%\Dayline\backups\`.
- **Logical day:** `today = (now − dayStartOffset).date()`; 30 s timer +
  monotonic/wall-clock jump detection for wake; DST-safe.
- **Threading:** IO on the main thread (small files, debounced watcher); week
  stats cached by `(path, mtime_ns, size)`. `QThreadPool` behind the same
  interface only if profiling shows jank.

## Requirement traceability (FR → module → test)

| FR | Module | Test | Status |
|---|---|---|---|
| FR-T1..T5 add/toggle/edit/priority/meta | `core/model.py`, `core/editor.py`, `TaskRow.qml`, `app_vm` slots | test_editor, test_actions | ✅ |
| FR-T3 children, FR-T9 subtasks | `core/model.py` (children_of, block ops) | test_model, test_surgical | ✅ |
| FR-T6 undo/redo (≥50) | `core/editor.py` UndoStack (snapshot) | test_editor | ✅ |
| FR-T7 reorder | `editor.move`, Alt+↑/↓ shortcuts | test_actions | ✅ |
| FR-T8 quick `!` syntax | `editor.parse_quick_syntax` | test_editor | ✅ |
| FR-T10 metadata chips data | `core/model.py` + `ui/viewmodels/task_model.py` | test_model | ✅ |
| FR-D1/§5.2 counting + progress ring | `core/stats.py`, `today_vm`, `ProgressRing.qml` | test_stats, test_shell_smoke | ✅ |
| FR-D2 day nav (Alt+←/→, Ctrl+T) | `app_vm` slots, `Main.qml` Shortcuts | test_shell_smoke | ✅ |
| FR-D3 To do/Done/Carried sections | `today_vm` lists, `TodayPage.qml` | test_shell_smoke | ✅ |
| FR-D4 stable priority sort | `today_vm._sort_key` | test_shell_smoke (todoList order) | ✅ |
| FR-D5 empty/loading/error/vault-missing states | `TodayPage`, `VaultSetupView`, `EmptyState`, `SkeletonItem`, `ErrorBanner` | screenshot QA | ✅ |
| FR-D6 "Carried over: N" chip | `today_vm.carriedOver`, `TodayPage` chip | test_shell_smoke | ✅ |
| FR-P9 theme tokens | `Theme.qml` + `platform/system_theme.py` | screenshot QA (both themes) | ✅ (live OS watch in M5) |
| FR-R1..R8 rollover | `core/rollover.py` | test_rollover (unit + 320-case properties) | ✅ |
| FR-R5 logical day | `core/clock.py` | test_clock | ✅ |
| FR-O1 vault discovery | `core/obsidian.py` find_vaults | test_obsidian | ✅ (setup UI M2) |
| FR-O2 daily-notes.json | `core/obsidian.py` read_daily_notes | test_obsidian | ✅ |
| FR-O3 Moment subset | `core/moment_format.py` | test_moment_format | ✅ |
| FR-O4/O7 section + round-trip | `core/parser.py`, `serializer.py` | test_roundtrip (2×1000 cases), test_surgical | ✅ |
| FR-O5 live two-way sync | `core/watcher.py`, `ui/sync.py` | test_watcher, test_actions | ✅ |
| FR-O6 open URI | `core/obsidian.py` open_uri | test_obsidian | ✅ (button M4) |
| FR-O9 legacy import | `core/settings.py` import_legacy_todo_config | test_settings | ✅ (Settings UI M4) |
| FR-O10 conflict copies | `core/obsidian.py` is_conflict_copy | test_obsidian | ✅ |
| §5.7 Store safe RMW + backups | `core/store.py` | test_store | ✅ |
| §3.7 settings persistence | `core/settings.py` | test_settings | ✅ |
| §5.9 wake/DST detection | `core/clock.py` detect_wake + `app_vm._on_tick` | test_clock | ✅ |

| FR-W1/W2 week rows + click-to-day | `ui/viewmodels/week_vm.py`, `WeekPage.qml` | test_week_settings_vm | ✅ |
| FR-W3 month heat-map | `week_vm.monthHeat`, `WeekPage` Grid | test_week_settings_vm | ✅ |
| FR-W5 cached stats ≤200ms | `core/stats.py` StatsService | test_stats | ✅ |
| §3.7 Settings live-apply | `ui/viewmodels/settings_vm.py`, `SettingsPage.qml` | test_week_settings_vm | ✅ |
| §3.8 Onboarding wizard | `Onboarding.qml`, `app_vm.firstRun` | screenshot QA | ✅ |
| FR-O9 legacy import | `settings_vm.importLegacy` | test_week_settings_vm | ✅ |

Remaining: Windows integration (M5); hardening (M6); "Open in Obsidian" button + release (M7).
