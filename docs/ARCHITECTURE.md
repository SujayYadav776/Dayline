# Architecture

## Layers (dependency rule: core ← viewmodels ← qml; `platform` injected; core imports nothing from other layers)

```
src/dayline/
├─ core/        pure Python, no Qt: model, parser, serializer, store, rollover,
│               stats, moment_format, obsidian discovery, settings, clock
├─ platform/    Windows adapters behind interfaces (autostart, single instance,
│               hotkey, notifications, tray, dwm, paths); fakes for tests
├─ ui/viewmodels/  QObject + QAbstractListModel bridges (today, task model, week, settings)
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
| FR-T1..T5 semantics (add/toggle/edit/priority/meta) | `core/model.py` | test_model, test_surgical | core ✅ (UI in M2/M3) |
| FR-T3 children, FR-T9 subtasks | `core/model.py` (children_of, block ops) | test_model, test_surgical | core ✅ |
| FR-T10 metadata chips data | `core/model.py` (split_description, tail) | test_model | core ✅ |
| FR-D1/§5.2 counting rules | `core/stats.py` | test_stats | core ✅ |
| FR-D4 stable priority sort data | `core/model.py` PRIO_RANK | — (VM in M3) | core ✅ |
| FR-R1..R8 rollover | `core/rollover.py` | test_rollover (unit + 320-case properties) | ✅ |
| FR-R5 logical day | `core/clock.py` | test_clock | ✅ |
| FR-O1 vault discovery | `core/obsidian.py` find_vaults | test_obsidian | ✅ |
| FR-O2 daily-notes.json | `core/obsidian.py` read_daily_notes | test_obsidian | ✅ |
| FR-O3 Moment subset | `core/moment_format.py` | test_moment_format | ✅ |
| FR-O4/O7 section + round-trip | `core/parser.py`, `serializer.py` | test_roundtrip (2×1000 cases), test_surgical | ✅ |
| FR-O6 open URI | `core/obsidian.py` open_uri | test_obsidian | ✅ |
| FR-O9 legacy import | `core/settings.py` import_legacy_todo_config | test_settings | ✅ |
| FR-O10 conflict copies | `core/obsidian.py` is_conflict_copy | test_obsidian | ✅ |
| §5.7 Store safe RMW + backups | `core/store.py` | test_store | ✅ |
| §3.7 settings persistence | `core/settings.py` | test_settings | ✅ |
| §5.9 wake/DST detection | `core/clock.py` detect_wake | test_clock | ✅ |

Layers untouched in M1: `platform/` (paths only), `ui/` — they start in M2.
