"""TaskEditor + UndoStack tests (FR-T1..T8, FR-T6)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from dayline.core.editor import StaleEditError, TaskEditor, parse_quick_syntax
from dayline.core.model import Priority
from dayline.core.store import Store

D = date(2026, 9, 19)


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    def path_for(d: date) -> Path:
        return tmp_path / f"{d.isoformat()}.md"

    path_for(D).parent.mkdir(exist_ok=True)
    return Store(path_for, sleep=lambda _s: None)


@pytest.fixture()
def editor(store: Store) -> TaskEditor:
    return TaskEditor(store)


def add(editor: TaskEditor, text: str) -> int:
    """Add a task and return its stable line key (asserts success)."""
    task = editor.add(D, text)
    assert task is not None
    return task.line_no


def text(store: Store) -> str:
    p = store.path_for(D)
    return p.read_text("utf-8") if p.is_file() else ""


# ---- quick syntax ----------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "clean", "prio"),
    [
        ("Buy milk !!!", "Buy milk", Priority.HIGH),
        ("Call mom !!", "Call mom", Priority.MEDIUM),
        ("Water plants !", "Water plants", Priority.LOW),
        ("Plain task", "Plain task", None),
        ("!!!", "!!!", None),  # bangs alone are not a task
        ("a !! b", "a !! b", None),  # bangs must be trailing
    ],
)
def test_parse_quick_syntax(raw: str, clean: str, prio: Priority | None) -> None:
    assert parse_quick_syntax(raw) == (clean, prio)


# ---- add -------------------------------------------------------------------
def test_add_creates_note_and_task(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "First task")
    assert text(store) == "## To-Do\n- [ ] First task\n"


def test_add_with_quick_priority(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "Urgent !!!")
    assert "- [ ] Urgent ⏫" in text(store)


def test_add_explicit_priority_beats_quick(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "X !!", priority=Priority.LOW)
    assert "- [ ] X 🔽" in text(store)


# ---- toggle / status / priority / edit -------------------------------------
def test_toggle_roundtrip(editor: TaskEditor, store: Store) -> None:
    key = add(editor, "Task")
    editor.toggle(D, key)
    assert "- [x] Task" in text(store)
    editor.toggle(D, key)
    assert "- [ ] Task" in text(store)


def test_set_priority_preserves_position(editor: TaskEditor, store: Store) -> None:
    key = add(editor, "Report 📅 2026-09-20")
    editor.set_priority(D, key, Priority.HIGH)
    assert "- [ ] Report 📅 2026-09-20 ⏫" in text(store)


def test_edit_text_preserves_tail(editor: TaskEditor, store: Store) -> None:
    key = add(editor, "Old 📅 2026-01-01")
    editor.edit_text(D, key, "New")
    assert "- [ ] New 📅 2026-01-01" in text(store)


# ---- delete / move ---------------------------------------------------------
def test_delete_removes_task(editor: TaskEditor, store: Store) -> None:
    a = add(editor, "A")
    add(editor, "B")
    editor.delete(D, a)
    body = text(store)
    assert "A" not in body and "B" in body


def test_move_reorders(editor: TaskEditor, store: Store) -> None:
    a = add(editor, "A")
    b = add(editor, "B")
    editor.move(D, a, None)  # A to end
    body = text(store)
    assert body.index("- [ ] B") < body.index("- [ ] A")
    editor.move(D, b, None)  # B to end — no crash


# ---- stale -----------------------------------------------------------------
def test_stale_edit_raises(editor: TaskEditor, store: Store) -> None:
    key = add(editor, "Task")
    # external edit removes the task line entirely → the key is now stale
    store.path_for(D).write_text("## To-Do\n", encoding="utf-8")
    with pytest.raises(StaleEditError):
        editor.toggle(D, key)


# ---- undo / redo -----------------------------------------------------------
def test_undo_add_restores_bytes(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "Keep")
    before = text(store)
    editor.add(D, "Temp")
    assert "Temp" in text(store)
    assert editor.undo() is True
    assert text(store) == before
    assert editor.redo() is True
    assert "Temp" in text(store)


def test_undo_toggle(editor: TaskEditor, store: Store) -> None:
    key = add(editor, "Task")
    editor.toggle(D, key)
    editor.undo()
    assert "- [ ] Task" in text(store)


def test_undo_created_note_leaves_empty_doc(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "First")
    editor.undo()
    body = text(store)
    assert "First" not in body
    assert body.startswith("## To-Do")  # never deletes; restores empty managed doc


def test_undo_stale_after_external_edit_is_skipped(editor: TaskEditor, store: Store) -> None:
    editor.add(D, "A")
    editor.add(D, "B")
    # external edit after our last op
    store.path_for(D).write_text("## To-Do\n- [ ] A\n- [ ] B\n- [ ] external\n", encoding="utf-8")
    assert editor.undo() is False  # refuses to clobber external edit


def test_undo_stack_limit() -> None:
    from dayline.core.editor import UndoStack

    u = UndoStack(limit=3)
    assert u._undo.maxlen == 3
