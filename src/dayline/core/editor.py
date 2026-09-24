"""TaskEditor: high-level note mutations + session undo/redo (PRD FR-T1..T8, FR-T6).

Every mutation runs through ``Store.mutate`` (fresh read-modify-write), so
concurrent Obsidian edits are never clobbered. Undo restores the exact bytes
captured before an action, but only if the file is unchanged since that action
(a stale undo is dropped, never applied blindly).
"""

from __future__ import annotations

import logging
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dayline.core.errors import DaylineError
from dayline.core.model import NoteDoc, Priority, StatusKind, Task
from dayline.core.store import Store

log = logging.getLogger("dayline.core.editor")


class StaleEditError(DaylineError):
    """The target task moved/vanished (external edit); reload before retrying."""


# FR-T8: trailing ! = low, !! = medium, !!! = high
_QUICK_RE = re.compile(r"^(.*?)(!{1,3})$", re.DOTALL)
_BANG_TO_PRIO = {1: Priority.LOW, 2: Priority.MEDIUM, 3: Priority.HIGH}

# 📅 due-date token (Obsidian Tasks format), rewritten on cross-day moves
_DUE_RE = re.compile(r"📅\s*\d{4}-\d{2}-\d{2}")


def parse_quick_syntax(text: str) -> tuple[str, Priority | None]:
    """Split trailing !/!!/!!! from the add-field text into (clean, priority)."""
    m = _QUICK_RE.match(text.strip())
    if m and m.group(1).strip():
        return m.group(1).strip(), _BANG_TO_PRIO[len(m.group(2))]
    return text.strip(), None


@dataclass
class _Snapshot:
    path: Path
    existed_before: bool
    before: bytes | None
    after: bytes


@dataclass
class _Op:
    label: str
    snapshots: list[_Snapshot]


class UndoStack:
    def __init__(self, limit: int = 100) -> None:
        self._undo: deque[_Op] = deque(maxlen=limit)
        self._redo: deque[_Op] = deque(maxlen=limit)

    def record(self, op: _Op) -> None:
        self._undo.append(op)
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def pop_undo(self) -> _Op | None:
        return self._undo.pop() if self._undo else None

    def pop_redo(self) -> _Op | None:
        return self._redo.pop() if self._redo else None

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()


class TaskEditor:
    def __init__(self, store: Store, undo: UndoStack | None = None) -> None:
        self.store = store
        self.undo_stack = undo or UndoStack()

    # -- helpers --------------------------------------------------------------
    def _apply(self, d: date, label: str, fn: Callable[[Store, date], Task | None]) -> Task | None:
        path = self.store.path_for(d)
        before = path.read_bytes() if path.is_file() else None
        existed = before is not None
        task = fn(self.store, d)
        if task is None:
            return None
        after = path.read_bytes()
        if after != before:
            self.undo_stack.record(_Op(label, [_Snapshot(path, existed, before, after)]))
        return task

    @staticmethod
    def _find(doc: NoteDoc, key: int) -> Task:
        for t in doc.tasks:
            if t.line_no == key:
                return t
        raise StaleEditError(f"task {key} no longer present")

    # -- mutations ------------------------------------------------------------
    def add(self, d: date, text: str, priority: Priority | None = None) -> Task | None:
        clean, quick = parse_quick_syntax(text)
        prio = priority or quick
        if not clean:
            return None

        def fn(store: Store, day: date) -> Task | None:
            return store.mutate(day, lambda doc: doc.add_task(clean, prio))

        return self._apply(d, "add", fn)

    def toggle(self, d: date, key: int) -> Task | None:
        """Flip a task's box. Completing a 🔁 recurring task also creates the
        next instance in its due day's note — both files in ONE undo op."""
        src_path = self.store.path_for(d)
        src_before = src_path.read_bytes() if src_path.is_file() else None

        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                t.toggle()
                return t

            return store.mutate(day, mut)

        task = fn(self.store, d)
        if task is None:
            return None
        snaps: list[_Snapshot] = []
        src_after = src_path.read_bytes() if src_path.is_file() else None
        if src_after is not None and src_after != src_before:
            snaps.append(_Snapshot(src_path, src_before is not None, src_before, src_after))
        if task.kind is StatusKind.DONE:
            snaps.extend(self._spawn_recurring(d, task))
        if snaps:
            self.undo_stack.record(_Op("toggle", snaps))
        return task

    def _spawn_recurring(self, d: date, task: Task) -> list[_Snapshot]:
        """After an open→done toggle: append the next 🔁 instance to its day's
        note. Returns the extra file snapshot(s) for the caller's undo op."""
        from dayline.core import recur

        rule = recur.rule_of(task.body)
        if not rule:
            return []
        due = recur.due_of(task.body)
        base = max(due, d) if due else d  # never spawn in the past
        nxt = recur.next_occurrence(rule, base)
        if nxt is None or nxt == d:
            return []
        raw = f"{task.indent}{task.marker}{task.sep}[ ] {recur.next_body(task.body, nxt)}"
        dst_path = self.store.path_for(nxt)
        before = dst_path.read_bytes() if dst_path.is_file() else None
        existed = before is not None

        def _add(doc: NoteDoc) -> bool:
            doc.add_task_lines([raw])
            return True

        self.store.mutate(nxt, _add)
        after = dst_path.read_bytes() if dst_path.is_file() else None
        if after is None or after == before:
            return []
        return [_Snapshot(dst_path, existed, before, after)]

    def set_status(self, d: date, key: int, ch: str) -> Task | None:
        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                t.set_status(ch)
                return t

            return store.mutate(day, mut)

        return self._apply(d, "status", fn)

    def edit_text(self, d: date, key: int, new_text: str) -> Task | None:
        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                t.set_description(new_text)
                return t

            return store.mutate(day, mut)

        return self._apply(d, "edit", fn)

    def set_priority(self, d: date, key: int, priority: Priority | None) -> Task | None:
        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                t.set_priority(priority)
                return t

            return store.mutate(day, mut)

        return self._apply(d, "priority", fn)

    def delete(self, d: date, key: int) -> bool:
        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                doc.delete_task(t)
                return t

            return store.mutate(day, mut)

        return self._apply(d, "delete", fn) is not None

    def move(self, d: date, key: int, before_key: int | None) -> Task | None:
        def fn(store: Store, day: date) -> Task | None:
            def mut(doc: NoteDoc) -> Task:
                t = self._find(doc, key)
                before = None if before_key is None else self._find(doc, before_key)
                doc.move_task_before(t, before)
                return t

            return store.mutate(day, mut)

        return self._apply(d, "move", fn)

    def move_to_day(self, src: date, key: int, dst: date) -> Task | None:
        """Reschedule: move a task's raw line between two daily notes.

        A 📅 due date on the line is rewritten to ``dst``; the line is
        otherwise copied verbatim. Both files are captured in ONE undo op.
        """
        if src == dst:
            return None
        src_path = self.store.path_for(src)
        dst_path = self.store.path_for(dst)
        src_before = src_path.read_bytes() if src_path.is_file() else None
        dst_before = dst_path.read_bytes() if dst_path.is_file() else None
        if src_before is None:
            return None

        raw = self._find(self.store.read_doc(src), key).render()
        if _DUE_RE.search(raw):
            raw = _DUE_RE.sub(f"📅 {dst.isoformat()}", raw)

        def _del(doc: NoteDoc) -> bool:
            doc.delete_task(self._find(doc, key))
            return True

        def _add(doc: NoteDoc) -> bool:
            doc.add_task_lines([raw])
            return True

        self.store.mutate(src, _del)
        self.store.mutate(dst, _add)

        snaps: list[_Snapshot] = []
        src_after = src_path.read_bytes() if src_path.is_file() else None
        if src_after is not None and src_after != src_before:
            snaps.append(_Snapshot(src_path, True, src_before, src_after))
        dst_after = dst_path.read_bytes() if dst_path.is_file() else None
        if dst_after is not None and dst_after != dst_before:
            snaps.append(_Snapshot(dst_path, dst_before is not None, dst_before, dst_after))
        if snaps:
            self.undo_stack.record(_Op("move-day", snaps))
        return None

    # -- undo / redo ----------------------------------------------------------
    def undo(self) -> bool:
        op = self.undo_stack.pop_undo()
        return self._restore(op, forward=False) if op else False

    def redo(self) -> bool:
        op = self.undo_stack.pop_redo()
        return self._restore(op, forward=True) if op else False

    def _restore(self, op: _Op | None, *, forward: bool) -> bool:
        if op is None:
            return False
        snaps = list(reversed(op.snapshots)) if not forward else op.snapshots
        applied: list[_Snapshot] = []
        for s in snaps:
            current = s.path.read_bytes() if s.path.is_file() else None
            # The state we expect to be leaving (undo: `after`; redo: what
            # undo wrote — the pre-image, or an empty managed doc for a note
            # we created, since undo never deletes files).
            if not forward:
                want = s.after
            else:
                want = s.before if s.before is not None else self._empty_bytes(s.path)
            if current != want and not (want is None and current is None):
                log.info("undo/redo stale for %s; skipping", s.path.name)
                return False  # external edit since; abandon this step
            target = s.before if not forward else s.after
            if target is None:
                # we created the note; undo → empty managed doc (never delete)
                target = self._empty_bytes(s.path)
            self.store.write_bytes(s.path, target)
            applied.append(s)
        # push onto the opposite stack
        stack = self.undo_stack._redo if not forward else self.undo_stack._undo
        stack.append(op)
        return True

    def _empty_bytes(self, path: Path) -> bytes:
        from dayline.core.parser import empty_doc
        from dayline.core.serializer import serialize

        doc = empty_doc(self.store.heading)
        doc.ensure_section()
        return serialize(doc)
