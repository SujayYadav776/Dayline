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
