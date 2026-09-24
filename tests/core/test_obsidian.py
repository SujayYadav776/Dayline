"""Obsidian discovery + note path tests (FR-O1/O2/O3/O6/O10)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from dayline.core.obsidian import (
    DailyNotesSettings,
    block_ref_of,
    find_vaults,
    is_conflict_copy,
    jump_uri,
    note_path,
    note_rel_no_ext,
    open_uri,
    read_daily_notes,
    search_uri,
)

D = date(2026, 9, 19)


def make_vault(tmp_path: Path, daily_json: dict[str, str] | None = None) -> Path:
    vault = tmp_path / "My Vault"
    (vault / ".obsidian").mkdir(parents=True)
    if daily_json is not None:
        (vault / ".obsidian" / "daily-notes.json").write_text(json.dumps(daily_json), "utf-8")
    return vault


def test_find_vaults_sorts_open_first(tmp_path: Path) -> None:
    cfg = tmp_path / "obsidian.json"
    cfg.write_text(
        json.dumps(
            {
                "vaults": {
                    "a": {"path": "C:/notes/alpha", "ts": 100},
                    "b": {"path": "C:/notes/Beta", "open": True, "ts": 50},
                    "bad": {"nope": 1},
                    "empty": {"path": "  "},
                }
            }
        ),
        "utf-8",
    )
    vaults = find_vaults(cfg)
    assert [v.name for v in vaults] == ["Beta", "alpha"]
    assert vaults[0].is_open


def test_find_vaults_tolerates_missing_or_broken(tmp_path: Path) -> None:
    assert find_vaults(tmp_path / "nope.json") == []
    bad = tmp_path / "bad.json"
    bad.write_text("{broken", "utf-8")
    assert find_vaults(bad) == []


def test_read_daily_notes_defaults_and_overrides(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    s = read_daily_notes(vault)
    assert s.folder == "Daily" and s.date_format == "YYYY-MM-DD" and s.template is None
    vault2 = make_vault(
        tmp_path / "2", {"folder": "Journal/Days", "format": "YYYY/MM", "template": "Tmpl"}
    )
    s2 = read_daily_notes(vault2)
    assert s2.folder == "Journal/Days" and s2.date_format == "YYYY/MM" and s2.template == "Tmpl"


def test_note_path_subfolders_and_suffix(tmp_path: Path) -> None:
    vault = make_vault(tmp_path)
    p = note_path(vault, DailyNotesSettings(folder="Daily", date_format="YYYY/MM/YYYY-MM-DD"), D)
    assert p == vault / "Daily" / "2026" / "09" / "2026-09-19.md"


def test_note_path_rejects_unsupported_format() -> None:
    import pytest

    from dayline.core.errors import UnsupportedFormatError

    with pytest.raises(UnsupportedFormatError):
        note_path(Path("x"), DailyNotesSettings(date_format="gggg-[W]ww"), D)


def test_open_uri_encodes_vault_and_path() -> None:
    uri = open_uri("My Vault", "Daily/2026-09-19")
    assert uri == "obsidian://open?vault=My%20Vault&file=Daily%2F2026-09-19"
    assert "%" in open_uri("vault & co #1", "x")


def test_rel_no_ext_with_folder() -> None:
    assert note_rel_no_ext(DailyNotesSettings(folder="Daily"), D) == "Daily/2026-09-19"


def test_conflict_copy_detection() -> None:
    assert is_conflict_copy("2026-09-19 (conflicted copy ADMIN 2026-09-19).md")
    assert is_conflict_copy("2026-09-19's conflicted copy.md")
    assert not is_conflict_copy("2026-09-19.md")


# ---- click-a-task → jump to its exact line ----------------------------------
def test_block_ref_of_detects_anchor() -> None:
    assert block_ref_of("- [ ] ship it ^tk42") == "tk42"
    assert block_ref_of("- [ ] ship it ^tk-42  ") == "tk-42"
    assert block_ref_of("- [ ] ship it") is None
    assert block_ref_of("- [ ] caret ^ inside, not trailing") is None
    assert block_ref_of("- [ ] bad ^not-an-id!") is None


def test_open_uri_with_block_anchor() -> None:
    uri = open_uri("vault", "Daily/2026-09-19", block="tk42")
    assert uri == "obsidian://open?vault=vault&file=Daily%2F2026-09-19%23%5Etk42"


def test_jump_uri_prefers_block_anchor() -> None:
    uri = jump_uri("vault", "Daily/2026-09-19", "- [ ] buy milk ^tk42", "buy milk")
    assert uri.startswith("obsidian://open?") and "%23%5Etk42" in uri


def test_jump_uri_falls_back_to_in_note_search() -> None:
    from urllib.parse import unquote, urlparse

    uri = jump_uri("vault", "Daily/2026-09-19", "- [ ] Buy oat milk", "Buy oat milk")
    assert uri.startswith("obsidian://search?vault=vault&query=")
    q = unquote(urlparse(uri).query.split("query=", 1)[1])
    assert q == 'file:"2026-09-19" "Buy oat milk"'


def test_jump_uri_cleans_and_caps_phrase() -> None:
    from urllib.parse import unquote

    uri = jump_uri("v", "Daily/x", "- [ ] a", '  he said "hi"   there  ' + "z" * 200)
    q = unquote(uri.split("query=", 1)[1])
    assert q.startswith('file:"x" "he said hi there z')
    # quoted phrase is capped at 80 chars: fixed prefix + 80 + closing quote
    inner = q[len('file:"x" "') : -1]
    assert len(inner) == 80
    assert "  " not in inner and chr(34) not in inner


def test_jump_uri_empty_description_opens_note() -> None:
    uri = jump_uri("vault", "Daily/2026-09-19", "- [ ]   ", "   ")
    assert uri == "obsidian://open?vault=vault&file=Daily%2F2026-09-19"


def test_search_uri_encodes_query() -> None:
    from urllib.parse import quote

    uri = search_uri("My Vault", 'file:"a b" "c &d"')
    assert uri == (
        "obsidian://search?vault=My%20Vault&query=" + quote('file:"a b" "c &d"', safe="")
    )
