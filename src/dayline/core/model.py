"""Core data model: statuses, priorities, metadata tokens, normalization.

Pure Python (no Qt). Byte-fidelity rules from PRD §5.2–§5.6.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------- statuses --


class StatusKind(Enum):
    OPEN = "open"
    DONE = "done"
    MOVED = "moved"
    CANCELLED = "cancelled"
    CUSTOM = "custom"


def status_kind(ch: str) -> StatusKind:
    """Map a raw status character to its kind (PRD §5.2)."""
    if ch in (" ", "/"):
        return StatusKind.OPEN
    if ch in ("x", "X"):
        return StatusKind.DONE
    if ch == ">":
        return StatusKind.MOVED
    if ch == "-":
        return StatusKind.CANCELLED
    return StatusKind.CUSTOM


# -------------------------------------------------------------- priorities --


class Priority(Enum):
    """5-level Obsidian Tasks priority (PRD §5.3). UI maps highest→High, lowest→Low."""

    HIGHEST = "🔺"
    HIGH = "⏫"
    MEDIUM = "🔼"
    LOW = "🔽"
    LOWEST = "⏬"


PRIORITY_EMOJI: dict[Priority, str] = {p: p.value for p in Priority}
EMOJI_PRIORITY: dict[str, Priority] = {v: k for k, v in PRIORITY_EMOJI.items()}
PRIO_RANK: dict[Priority | None, int] = {
    Priority.HIGHEST: 0,
    Priority.HIGH: 1,
    Priority.MEDIUM: 2,
    Priority.LOW: 3,
    Priority.LOWEST: 4,
    None: 5,
}

# --------------------------------------------------------------- metadata ---

DUE, SCHEDULED, START, CREATED, DONE_ON, RECURRENCE = "📅", "⏳", "🛫", "➕", "✅", "🔁"
DATE_TOKENS = (DUE, SCHEDULED, START, CREATED, DONE_ON)
ALL_TOKEN_EMOJIS = frozenset(EMOJI_PRIORITY) | {DUE, SCHEDULED, START, CREATED, DONE_ON, RECURRENCE}

_DATE_TOKEN_RE = re.compile(r"[📅⏳🛫➕✅]\s*\d{4}-\d{2}-\d{2}")
_SIMPLE_DATELESS_RE = re.compile(r"[📅⏳🛫➕✅](?!\s*\d{4}-\d{2}-\d{2})")
# priority emoji anywhere in the line (first occurrence wins, position preserved)
_PRIORITY_TOKEN_RE = re.compile(r"[🔺⏫🔼🔽⏬]")
# recurrence emoji + everything up to the next token / tag / block-id / EOL
_RECURRENCE_TOKEN_RE = re.compile(r"🔁[^📅⏳🛫➕✅🔁🔺⏫🔼🔽⏬#]*")
_TAG_RE = re.compile(r"(?<!\S)#[^\s#]+")
_BLOCK_ID_RE = re.compile(r"\s*\^[A-Za-z0-9-]+(?=\s|$)")


def first_token_pos(body: str) -> int | None:
    """Index where the preserved metadata tail starts (first recognized emoji)."""
    best: int | None = None
    for emo in ALL_TOKEN_EMOJIS:
        i = body.find(emo)
        if i != -1 and (best is None or i < best):
            best = i
    return best


def split_description(body: str) -> tuple[str, str]:
    """('Write report ', '📅 2026-09-20 ⏫') — raw split at first recognized token.

    The tail is kept verbatim so edits never reorder the user's metadata.
    """
    pos = first_token_pos(body)
    if pos is None:
        return body, ""
    return body[:pos].rstrip(), body[pos:]


def strip_tokens(body: str) -> str:
    """Remove every recognized Tasks token (used for display/normalize)."""
    text = _RECURRENCE_TOKEN_RE.sub(" ", body)
    text = _DATE_TOKEN_RE.sub(" ", text)
    text = _PRIORITY_TOKEN_RE.sub(" ", text)
    text = _SIMPLE_DATELESS_RE.sub(" ", text)
    text = _BLOCK_ID_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    return text


def normalize(text: str) -> str:
    """Rollover dedupe key (PRD §5.5): strip tokens, lowercase, collapse whitespace."""
    return " ".join(strip_tokens(text).lower().split())


def parse_priority(body: str) -> tuple[Priority | None, int]:
    """Priority emoji in body; returns (priority, index) or (None, -1)."""
    best: tuple[int, Priority] | None = None
    for i, ch in enumerate(body):
        prio = EMOJI_PRIORITY.get(ch)
        if prio is not None and (best is None or i < best[0]):
            best = (i, prio)
    return (best[1], best[0]) if best else (None, -1)


def apply_priority(body: str, new: Priority | None) -> str:
    """Set priority preserving position; appends only when none existed (PRD §5.3)."""
    old, idx = parse_priority(body)
    if old is not None:
        if new is None:
            before, after = body[:idx], body[idx + 1 :]
            if before.endswith(" "):
                before = before[:-1]
            elif after.startswith(" "):
                after = after[1:]
            return (before + after).rstrip()
        if old is new:
            return body
        return body[:idx] + new.value + body[idx + 1 :]
    if new is None:
        return body
    return f"{body.rstrip()} {new.value}" if body.strip() else new.value


# ------------------------------------------------------------------ tasks ---

# indent marker sep [status] gap body
TASK_RE = re.compile(r"^([ \t]*)([-*+])([ \t]+)\[([^\]\n])\]([ \t]*)(.*)$")


@dataclass
class Task:
    """One checkbox line. `dirty` marks a line that may be re-serialized;
    untouched tasks round-trip byte-for-byte (invariant §4.1)."""

    line_no: int
    indent: str
    marker: str
    sep: str
    status_char: str
    gap: str
    body: str
    dirty: bool = False

    # -- derived ------------------------------------------------------------
    @property
    def kind(self) -> StatusKind:
        return status_kind(self.status_char)

    @property
    def priority(self) -> Priority | None:
        return parse_priority(self.body)[0]

    @property
    def description(self) -> str:
        return strip_tokens(self.body).strip()

    @property
    def normalized(self) -> str:
        return normalize(self.body)

    def visual_indent(self, tab: int = 4) -> int:
        return len(self.indent.replace("\t", " " * tab))

    # -- mutations (mark dirty; serializer rebuilds the line) ------------------
    def set_status(self, ch: str) -> None:
        if ch != self.status_char:
            self.status_char = ch
            self.dirty = True

    def toggle(self) -> None:
        """UI toggle writes only ' ' or 'x' (PRD §5.2)."""
        self.set_status(" " if self.kind is StatusKind.DONE else "x")

    def set_priority(self, new: Priority | None) -> None:
        applied = apply_priority(self.body, new)
        if applied != self.body:
            self.body = applied
            self.dirty = True

    def set_description(self, new_desc: str) -> None:
        new_desc = re.sub(r"[\r\n]+", " ", new_desc).strip()
        _desc, tail = split_description(self.body)
        rebuilt = f"{new_desc} {tail}".strip() if new_desc and tail else (new_desc or tail)
        if rebuilt != self.body:
            self.body = rebuilt
            self.dirty = True

    def open_copy(self) -> Task:
        """Copy for rollover: same raw fields, status reset to open (FR-R4)."""
        return Task(
            line_no=-1,
            indent=self.indent,
            marker=self.marker,
            sep=self.sep,
            status_char=" ",
            gap=self.gap,
            body=self.body,
            dirty=True,
        )

    def render(self) -> str:
        gap = self.gap or (" " if self.body else "")
        return f"{self.indent}{self.marker}{self.sep}[{self.status_char}]{gap}{self.body}"


@dataclass
class RawLine:
    """A physical line: text without its terminator plus the exact terminator."""

    text: str
    ending: str  # '\n', '\r\n', '\r' or '' (last line without trailing newline)

    def raw(self) -> str:
        return self.text + self.ending


# -------------------------------------------------------------------- doc ---


@dataclass
class Section:
    heading_no: int
    start: int  # first content line index
    end: int  # exclusive: next same-or-higher heading, or EOF


@dataclass
class NoteDoc:
    """A daily note: raw lines + parsed managed section (PRD §5.1).

    Structural edits materialize dirty lines then rescan, so every
    untouched line keeps its exact original bytes through serialization.
    """

    lines: list[RawLine]
    bom: bool = False
    eol: str = "\n"
    heading: str = "## To-Do"
    heading_level: int = 2
    section: Section | None = None
    tasks: list[Task] = field(default_factory=list)

    # -- parsing ---------------------------------------------------------------
    def rescan(self) -> None:
        self.section, self.tasks = _scan(self.lines, self.heading, self.heading_level)

    def flush_dirty(self) -> None:
        for t in self.tasks:
            if t.dirty:
                self.lines[t.line_no].text = t.render()
                t.dirty = False

    # -- structure helpers -------------------------------------------------------
    def top_level_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.visual_indent() == 0]

    def children_of(self, task: Task) -> list[Task]:
        """Contiguous following task lines with strictly deeper indent."""
        out: list[Task] = []
        base = task.visual_indent()
        for t in self.tasks:
            if t.line_no <= task.line_no:
                continue
            if t.line_no != task.line_no + 1 + len(out):
                break
            if t.visual_indent() > base:
                out.append(t)
            else:
                break
        return out

    def block_len(self, task: Task) -> int:
        """1 + number of contiguous child task lines."""
        n = 1
        for c in self.children_of(task):
            if c.line_no == task.line_no + n:
                n += 1
        return n

    def _insert_lines(self, at: int, new: list[RawLine]) -> None:
        if not new:
            return
        # keep terminators consistent: a previously unterminated EOF line gains eol
        if self.lines and self.lines[-1].ending == "" and at >= len(self.lines):
            self.lines[-1].ending = self.eol
        new[-1].ending = self.eol
        for off, line in enumerate(new):
            self.lines.insert(at + off, line)
        self._shift_positions(at, len(new))

    def _shift_positions(self, at: int, delta: int) -> None:
        for t in self.tasks:
            if t.line_no >= at:
                t.line_no += delta
        if self.section:
            for name in ("heading_no", "start", "end"):
                v = getattr(self.section, name)
                if v >= at:
                    setattr(self.section, name, v + delta)

    def _delete_lines(self, start: int, count: int) -> None:
        del self.lines[start : start + count]
        self._shift_positions(start, -count)

    def ensure_section(self) -> Section:
        if self.section is not None:
            return self.section
        self.flush_dirty()
        idx = len(self.lines)
        if self.lines and self.lines[-1].text.strip():
            self._insert_lines(idx, [RawLine("", self.eol)])
            idx += 1
        self._insert_lines(idx, [RawLine(self.heading, self.eol)])
        self.section = Section(heading_no=idx, start=idx + 1, end=idx + 1)
        self.rescan()
        assert self.section is not None
        return self.section

    # -- task-level API ----------------------------------------------------------
    def _append_position(self) -> int:
        """Insertion index: after the last non-blank line of the section."""
        assert self.section is not None
        i = self.section.end
        while i > self.section.start and self.lines[i - 1].text.strip() == "":
            i -= 1
        return i

    def add_task(self, description: str, priority: Priority | None = None) -> Task:
        desc = re.sub(r"[\r\n]+", " ", description).strip()
        body = apply_priority(desc, priority) if desc else (priority.value if priority else "")
        self.ensure_section()
        pos = self._append_position()
        self._insert_lines(pos, [RawLine(f"- [ ] {body}", self.eol)])
        self.rescan()
        return next(t for t in self.tasks if t.line_no == pos)

    def add_task_lines(self, raw_texts: list[str]) -> None:
        """Append pre-rendered task lines (rollover copies bodies verbatim)."""
        self.ensure_section()
        pos = self._append_position()
        self._insert_lines(pos, [RawLine(t, self.eol) for t in raw_texts])
        self.rescan()

    def delete_task(self, task: Task) -> None:
        self.flush_dirty()
        count = self.block_len(task)
        self._delete_lines(task.line_no, count)
        self.rescan()

    def move_task_before(self, task: Task, before: Task | None) -> None:
        """Move the block (with children) before `before`, or to section end."""
        self.flush_dirty()
        count = self.block_len(task)
        block = self.lines[task.line_no : task.line_no + count]
        self._delete_lines(task.line_no, count)
        self.rescan()  # refresh positions after removal
        target = self._append_position() if before is None else before.line_no
        self._insert_lines(target, list(block))
        self.rescan()


def _scan(lines: list[RawLine], heading: str, level: int) -> tuple[Section | None, list[Task]]:
    end_re = re.compile(rf"^#{{{1},{level}}}\s")
    fm_start = 0
    if lines and lines[0].text.strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].text.strip() in ("---", "..."):
                fm_start = i + 1
                break
    heading_no = -1
    want = heading.strip().lower()
    for i in range(fm_start, len(lines)):
        if lines[i].text.strip().lower() == want:
            heading_no = i
            break
    if heading_no == -1:
        return None, []
    end = len(lines)
    for i in range(heading_no + 1, len(lines)):
        if end_re.match(lines[i].text):
            end = i
            break
    tasks: list[Task] = []
    for i in range(heading_no + 1, end):
        m = TASK_RE.match(lines[i].text)
        if m:
            tasks.append(
                Task(
                    line_no=i,
                    indent=m.group(1),
                    marker=m.group(2),
                    sep=m.group(3),
                    status_char=m.group(4),
                    gap=m.group(5),
                    body=m.group(6),
                )
            )
    return Section(heading_no=heading_no, start=heading_no + 1, end=end), tasks
