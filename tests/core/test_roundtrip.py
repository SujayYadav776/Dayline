"""Property-based round-trip fidelity (PRD §5.6, success metric §1.6).

Parse→serialize of an UNMODIFIED note must be byte-identical: BOM, CRLF/LF/CR,
trailing newline, tabs, weird spacing, front-matter, non-ASCII all preserved.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dayline.core.parser import parse_bytes, parse_text
from dayline.core.serializer import serialize

# characters that stress the splitter without being line breaks
_SAFE_CHARS = st.sampled_from(
    [
        *list("abcXYZ -[]*+#^/\t:.'\"<>?!()[]{},;%&=_~`|@0123456789"),
        *["\x0c", "é", "中文", "😀", "⏫", "📅", "→"],
    ]
)
_line = (
    st.lists(_SAFE_CHARS, max_size=40)
    .map("".join)
    .map(lambda s: s.replace("\r", "").replace("\n", ""))
)

_LINE_KINDS = st.one_of(
    _line,
    st.just("## To-Do"),
    st.just("## to-do"),
    st.just("# H1"),
    st.just("### H3"),
    st.just("---"),
    st.just(""),
    st.just("- [ ] plain task"),
    st.just("-   [X]	 odd spacing ⏫"),
    st.just("  - [?] custom status"),
    st.just("\t- [/] tabbed in progress"),
    st.just("- [ ] task with trailing spaces   "),
    st.just("text #tag ^blockid 📅 2026-01-01 🔁 every week"),
)


@st.composite
def note_bytes(draw: st.DrawFn) -> bytes:
    lines = draw(st.lists(_LINE_KINDS, max_size=25))
    eol = draw(st.sampled_from(["\n", "\r\n", "\r"]))
    per_line_eol = draw(st.booleans())  # mixed line endings
    text = ""
    for i, ln in enumerate(lines):
        text += ln
        if i != len(lines) - 1 or draw(st.booleans()):
            text += draw(st.sampled_from([eol, "\n", "\r\n"])) if per_line_eol else eol
    bom = draw(st.booleans())
    raw = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + raw) if bom else raw


@settings(max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(note_bytes())
def test_roundtrip_is_byte_identical(raw: bytes) -> None:
    doc = parse_bytes(raw)
    assert serialize(doc) == raw


@settings(max_examples=1000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(note_bytes())
def test_rescan_is_stable(raw: bytes) -> None:
    doc = parse_bytes(raw)
    doc.rescan()
    doc.rescan()
    assert serialize(doc) == raw


def test_text_roundtrip_simple() -> None:
    text = "front\n\n## To-Do\r\n- [x] done ⏫\r\n\r\n## Journal\r\ntext\r\n"
    doc = parse_text(text)
    assert "".join(ln.raw() for ln in doc.lines) == text
