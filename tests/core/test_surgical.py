"""Surgical editing + structural ops: untouched lines stay byte-identical."""

from __future__ import annotations

from dayline.core.model import Priority
from dayline.core.parser import parse_bytes, parse_text
from dayline.core.serializer import serialize

BASE = (
    "---\n"
    "tags: [daily]\n"
    "---\n"
    "Freeform stuff #keep\n"
    "\n"
    "## To-Do\n"
    "- [ ] Write report ⏫\n"
    "    - [ ] gather data\n"
    "- [x] Email Sam 📅 2026-09-20\n"
    "\n"
    "## Journal\n"
    "Anything else stays exactly as is.\n"
)


def lines_of(b: bytes) -> list[str]:
    return b.decode("utf-8").split("\n")


def test_toggle_only_touches_its_line() -> None:
    raw = BASE.encode()
    doc = parse_bytes(raw)
    doc.tasks[0].toggle()
    out = serialize(doc)
    old, new = lines_of(raw), lines_of(out)
    assert len(old) == len(new)
    diff = [i for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    assert diff == [6]  # only the toggled task line (0-based)
    assert new[6] == "- [x] Write report ⏫"
    assert old[7] == new[7]  # child untouched


def test_priority_change_preserves_position_and_tail() -> None:
    doc = parse_text("## To-Do\n- [ ] b ⏫ tail #t\n")
    doc.tasks[0].set_priority(Priority.LOW)
    assert serialize(doc).decode() == "## To-Do\n- [ ] b 🔽 tail #t\n"


def test_add_task_creates_section_when_missing() -> None:
    doc = parse_text("# Day\nnotes here")
    doc.add_task("new task", Priority.HIGH)
    out = serialize(doc).decode()
    assert out == "# Day\nnotes here\n\n## To-Do\n- [ ] new task ⏫\n"


def test_add_task_appends_at_section_end_before_blank_tail() -> None:
    doc = parse_text("## To-Do\n- [ ] one\n\n## Journal\nJ\n")
    doc.add_task("two")
    assert serialize(doc).decode() == "## To-Do\n- [ ] one\n- [ ] two\n\n## Journal\nJ\n"


def test_delete_task_cascades_children_only() -> None:
    src = "## To-Do\n- [ ] p1\n    - [ ] c1\n        - [ ] c2\n- [ ] p2\n\n## Journal\n"
    doc = parse_text(src)
    doc.delete_task(doc.tasks[0])
    out = serialize(doc).decode()
    assert out == "## To-Do\n- [ ] p2\n\n## Journal\n"


def test_move_task_carries_children_and_lands_before_target() -> None:
    src = "## To-Do\n- [ ] A\n    - [ ] a1\n- [ ] B\n- [ ] C\n"
    doc = parse_text(src)
    a = doc.tasks[0]
    c = next(t for t in doc.tasks if t.body == "C")
    doc.move_task_before(a, c)
    out = serialize(doc).decode()
    assert out == "## To-Do\n- [ ] B\n- [ ] A\n    - [ ] a1\n- [ ] C\n"


def test_move_to_section_end() -> None:
    src = "## To-Do\n- [ ] A\n- [ ] B\n- [ ] C\n"
    doc = parse_text(src)
    a = doc.tasks[0]
    doc.move_task_before(a, None)
    assert serialize(doc).decode() == "## To-Do\n- [ ] B\n- [ ] C\n- [ ] A\n"


def test_crlf_and_bom_survive_edits() -> None:
    raw = b"\xef\xbb\xbf## To-Do\r\n- [ ] one\r\n- [x] two\r\n"
    doc = parse_bytes(raw)
    doc.tasks[0].toggle()
    out = serialize(doc)
    assert out.startswith(b"\xef\xbb\xbf")
    assert out.count(b"\r\n") == 3 and b"\n\r" not in out
    assert out == b"\xef\xbb\xbf## To-Do\r\n- [x] one\r\n- [x] two\r\n"


def test_edit_description_preserves_tail_order() -> None:
    doc = parse_text("## To-Do\n- [ ]  Old   text 📅 2026-02-02 🔁 weekly #w\n")
    t = doc.tasks[0]
    t.set_description("New text")
    assert t.body == "New text 📅 2026-02-02 🔁 weekly #w"
    assert (
        serialize(doc).decode() == "## To-Do\n- [ ]  New text 📅 2026-02-02 🔁 weekly #w\n"
    )  # gap kept


def test_lower_heading_match_is_case_insensitive() -> None:
    doc = parse_text("## to-do\n- [ ] x\n", heading="## To-Do")
    assert doc.section is not None and len(doc.tasks) == 1


def test_section_ends_only_at_same_or_higher_level() -> None:
    doc = parse_text("## To-Do\n- [ ] a\n### Sub\n- [ ] b\n## Next\n- [ ] c\n")
    assert [t.body for t in doc.tasks] == ["a", "b"]  # h3 doesn't end section; h2 does


def test_heading_inside_frontmatter_not_matched() -> None:
    doc = parse_text("---\n## To-Do\n---\n- [ ] outside\n")
    assert doc.section is None or doc.section.heading_no >= 3
