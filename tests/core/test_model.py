"""Unit tests for core.model: statuses, priorities, normalization, surgical fields."""

from __future__ import annotations

from dayline.core.model import (
    Priority,
    StatusKind,
    Task,
    apply_priority,
    normalize,
    split_description,
    status_kind,
    strip_tokens,
)
from dayline.core.parser import parse_text


def test_status_kinds() -> None:
    assert status_kind(" ") is StatusKind.OPEN
    assert status_kind("/") is StatusKind.OPEN
    assert status_kind("x") is StatusKind.DONE and status_kind("X") is StatusKind.DONE
    assert status_kind(">") is StatusKind.MOVED
    assert status_kind("-") is StatusKind.CANCELLED
    assert status_kind("?") is StatusKind.CUSTOM


def test_priority_parse_and_replace_in_place() -> None:
    body = "Review paper ⏫ 📅 2026-09-20"
    assert apply_priority(body, Priority.LOW) == "Review paper 🔽 📅 2026-09-20"
    assert apply_priority(body, None) == "Review paper 📅 2026-09-20"
    assert apply_priority("no emoji", Priority.HIGH) == "no emoji ⏫"
    assert apply_priority("⏫ leading", Priority.MEDIUM) == "🔼 leading"


def test_priority_enum_covers_five_levels() -> None:
    assert {p.value for p in Priority} == {"🔺", "⏫", "🔼", "🔽", "⏬"}


def test_normalize_strips_tokens_lowercases_collapses() -> None:
    a = normalize("Buy  Milk ⏫ 📅 2026-09-20 #errand ^abc123")
    b = normalize("buy milk 🔁 every week")
    assert a == "buy milk"
    assert b == "buy milk"
    assert normalize("Buy milk") == a


def test_split_description_keeps_tail_verbatim() -> None:
    desc, tail = split_description("Write report 📅 2026-01-01 ⏫")
    assert desc == "Write report"
    assert tail == "📅 2026-01-01 ⏫"
    assert split_description("plain text") == ("plain text", "")


def test_strip_tokens_keeps_links_and_weird_emoji() -> None:
    assert (
        strip_tokens("ping [[Team Sync]] about 🧪 lab ⏫").strip()
        == "ping [[Team Sync]] about 🧪 lab"
    )


def make_task(**kw: object) -> Task:
    base = {
        "line_no": 0,
        "indent": "",
        "marker": "-",
        "sep": " ",
        "status_char": " ",
        "gap": " ",
        "body": "t",
    }
    base.update(kw)
    return Task(**base)  # type: ignore[arg-type]


def test_task_toggle_writes_only_space_or_x() -> None:
    t = make_task(status_char="X")
    t.toggle()
    assert t.status_char == " "
    t2 = make_task(status_char="?")  # custom → toggling to done uses 'x'
    t2.toggle()
    assert t2.status_char == "x"


def test_task_render_preserves_raw_spacing() -> None:
    t = make_task(indent="  ", marker="*", sep="  ", gap="", status_char="/", body="deep")
    assert t.render() == "  *  [/] deep"  # '] ' space re-added: Obsidian needs it
    t2 = make_task(gap="", body="")
    assert t2.render() == "- [ ]"  # empty body: no trailing space


def test_task_set_description_preserves_tail() -> None:
    t = make_task(body="Old text 📅 2026-05-05 🔁 daily")
    t.set_description("New text")
    assert t.body == "New text 📅 2026-05-05 🔁 daily"
    assert t.dirty


def test_open_copy_resets_status_keeps_body() -> None:
    t = make_task(status_char=" ", indent="\t", body="sub ⏫")
    c = t.open_copy()
    assert c.status_char == " " and c.body == "sub ⏫" and c.indent == "\t"


def test_children_and_block_len() -> None:
    doc = parse_text(
        "## To-Do\n- [ ] parent\n    - [ ] child a\n        - [x] grandchild\n- [ ] sibling\n"
    )
    parent, _ca, _gc, sib = doc.tasks
    assert [t.body for t in doc.children_of(parent)] == ["child a", "grandchild"]
    assert doc.block_len(parent) == 3
    assert doc.block_len(sib) == 1
    assert [t.body for t in doc.top_level_tasks()] == ["parent", "sibling"]


def test_tab_indents_count_visually() -> None:
    doc = parse_text("## To-Do\n- [ ] p\n\t- [ ] c\n")
    assert doc.tasks[1].visual_indent() == 4


def test_note_rawline_repr_roundtrip_single_cr() -> None:
    doc = parse_text("a\rb\r\n")
    assert [(ln.text, ln.ending) for ln in doc.lines] == [("a", "\r"), ("b", "\r\n")]
