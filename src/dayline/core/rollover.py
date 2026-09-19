"""Rollover: carry unfinished tasks forward (PRD §5.5, normative algorithm).

Properties guaranteed by tests: idempotent · no task loss · untouched
content byte-identical · order preserved (older first) · metadata/priority
preserved · cancelled & unknown statuses never carried.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

from dayline.core.model import NoteDoc, StatusKind

if TYPE_CHECKING:  # pragma: no cover
    from dayline.core.store import Store

log = logging.getLogger("dayline.core.rollover")

_CARRY_STATUSES = frozenset({" ", "/"})  # open kinds only (FR-R8)


@dataclass
class RolloverResult:
    moved: int = 0
    marked_days: int = 0
    per_day: dict[date, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.moved > 0 or self.marked_days > 0


def rollover(store: Store, today: date, lookback: int) -> RolloverResult:
    """Plan against fresh reads, then write copies to today FIRST and mark
    sources '>' after: a crash between the phases can duplicate a task in
    memory only (dedupe suppresses it next run) and can never lose one."""
    result = RolloverResult()
    today_doc = store.read_doc(today)
    seen: set[str] = {
        t.normalized
        for t in today_doc.tasks
        if t.kind in (StatusKind.OPEN, StatusKind.DONE, StatusKind.MOVED)
    }

    # ---- phase 1: plan (reads only) --------------------------------------
    marks: dict[date, set[str]] = {}
    copies: list[list[str]] = []  # raw task lines, oldest-first
    for offset in range(lookback, 0, -1):
        d = today - timedelta(days=offset)
        if not store.exists(d):
            continue
        doc = store.read_doc(d)
        day_marks: set[str] = set()
        for t in doc.top_level_tasks():
            if t.status_char not in _CARRY_STATUSES:
                continue  # done/moved/cancelled/custom untouched (FR-R8)
            day_marks.add(t.normalized)
            if t.normalized not in seen:
                seen.add(t.normalized)
                block = [t.open_copy().render()]
                block += [c.open_copy().render() for c in doc.children_of(t)]
                copies.append(block)
                result.moved += 1
                result.per_day[d] = result.per_day.get(d, 0) + 1
        if day_marks:
            marks[d] = day_marks

    # ---- phase 2: append copies to today -----------------------------------
    if copies:

        def _append(doc: NoteDoc) -> bool:
            for block in copies:
                doc.add_task_lines(block)
            return True

        store.mutate(today, _append)

    # ---- phase 3: mark sources '>' (idempotent via status recheck) ----------
    for d, norms in marks.items():

        def _mark(doc: NoteDoc, _norms: set[str] = norms) -> bool:
            changed = False
            for t in doc.top_level_tasks():
                if t.status_char in _CARRY_STATUSES and t.normalized in _norms:
                    t.set_status(">")
                    changed = True
            return changed

        store.mutate(d, _mark)
        result.marked_days += 1

    log.info("rollover: moved=%d marked_days=%d", result.moved, result.marked_days)
    return result
