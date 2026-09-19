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

## Requirement traceability (FR → module → test) — filled during M1–M5

| FR | Module | Test | Status |
|---|---|---|---|
| — | — | — | not yet implemented |
