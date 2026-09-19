"""Store safety contract tests (PRD §5.7)."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from dayline.core.errors import LockedFileError
from dayline.core.model import NoteDoc
from dayline.core.store import Store

D0 = date(2026, 9, 19)
D1 = date(2026, 9, 20)


@pytest.fixture()
def vault(tmp_path: Path) -> Store:
    def path_for(d: date) -> Path:
        return tmp_path / "Daily" / f"{d.isoformat()}.md"

    path_for(D0).parent.mkdir(parents=True, exist_ok=True)
    return Store(path_for)


def add_one(doc: NoteDoc) -> bool:
    doc.add_task("written via store")
    return True


def test_mutate_creates_missing_note(vault: Store) -> None:
    vault.mutate(D0, add_one)
    assert vault.path_for(D0).read_text("utf-8") == "## To-Do\n- [ ] written via store\n"


def test_mutate_falsy_result_skips_write(vault: Store) -> None:
    vault.mutate(D0, lambda d: (d.add_task("x"), False)[1])
    assert not vault.path_for(D0).exists()


def test_mutate_identical_no_touch(vault: Store) -> None:
    vault.mutate(D0, add_one)
    before = os.stat(vault.path_for(D0))
    vault.mutate(D0, lambda d: True)  # no changes
    assert os.stat(vault.path_for(D0)) == before


def test_fresh_read_sees_external_edit(vault: Store, tmp_path: Path) -> None:
    vault.mutate(D0, add_one)
    # external write between UI load and mutation — fresh RMW must merge it
    external = "## To-Do\n- [ ] typed in obsidian\n"
    p = vault.path_for(D0)

    def fn(doc: NoteDoc) -> bool:
        # simulate: at fn-time, disk content is external (already re-read by store)
        assert doc.tasks[0].body == "typed in obsidian"
        doc.tasks[0].toggle()
        return True

    p.write_text(external, encoding="utf-8")
    vault.mutate(D0, fn)
    assert "- [x] typed in obsidian" in p.read_text("utf-8")


def test_race_detected_and_retried(vault: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    vault.mutate(D0, lambda d: d.add_task("base") and True)
    calls = {"n": 0}
    real_read = Path.read_bytes

    def racing_read(self: Path, *a: Any, **k: Any) -> bytes:
        if self.suffix == ".md" and calls["n"] == 0:
            calls["n"] += 1
            # after we parsed, an external writer touches the file
            Path.write_text(self, real_read(self).decode() + "\n## External\n", encoding="utf-8")
        return real_read(self, *a, **k)

    monkeypatch.setattr(Path, "read_bytes", racing_read)
    result = vault.mutate(D0, lambda d: d.add_task("mine") and True)
    monkeypatch.undo()
    assert result is True
    text = vault.path_for(D0).read_text("utf-8")
    assert "## External" in text and "- [ ] mine" in text  # merged on retry


def test_locked_file_retries_then_errors(vault: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    vault._sleep = slept.append  # inject no-op sleeper

    attempts = {"n": 0}

    def always_locked(src: str, dst: str) -> None:
        attempts["n"] += 1
        raise PermissionError(13, "locked")

    monkeypatch.setattr(os, "replace", always_locked)
    with pytest.raises(LockedFileError):
        vault.mutate(D0, add_one)
    assert attempts["n"] == 6  # 1 + 5 backoff retries
    assert slept == [0.05, 0.1, 0.2, 0.4, 0.8]


def test_no_temp_files_left_after_success(vault: Store, tmp_path: Path) -> None:
    vault.mutate(D0, add_one)
    stray = [p for p in (tmp_path / "Daily").iterdir() if p.name.startswith(".")]
    assert stray == []


def test_backups_written_and_pruned(tmp_path: Path) -> None:
    fixed = datetime(2026, 9, 19, 12, 0, 0)
    backups = tmp_path / "backups"

    def path_for(d: date) -> Path:
        return tmp_path / "Daily" / f"{d.isoformat()}.md"

    path_for(D0).parent.mkdir(parents=True)
    s = Store(
        path_for,
        backups_dir=backups,
        backup_keep_days=7,
        now=lambda: fixed,
        sleep=lambda _s: None,
    )
    s.mutate(D0, lambda d: d.add_task("first") and True)
    s.mutate(D0, add_one)  # modifies existing note → backup of previous bytes
    day_dir = backups / "2026-09-19"
    assert day_dir.is_dir()
    assert next(iter(day_dir.glob("*.md"))).read_text("utf-8") == "## To-Do\n- [ ] first\n"
    # an old backup folder is pruned on next write
    old = backups / "2026-08-01"
    old.mkdir(parents=True)
    (old / "x.md").write_text("stale")
    s.mutate(D0, lambda d: d.add_task("third") and True)
    assert not old.exists()


def test_own_write_suppression_roundtrip(vault: Store) -> None:
    vault.mutate(D0, add_one)
    p = vault.path_for(D0)
    assert vault.is_own_write(p) is True
    vault.forget_own_write(p)
    assert vault.is_own_write(p) is False
    vault.mutate(D0, lambda d: d.add_task("second") and True)
    assert vault.is_own_write(p) is True
    p.write_bytes(b"changed externally")
    assert vault.is_own_write(p) is False


def test_unicode_and_readonly_content(vault: Store) -> None:
    vault.mutate(D0, lambda d: d.add_task("检查 🧪 emoji ✓") and True)
    assert "检查 🧪" in vault.path_for(D0).read_text("utf-8")


def test_500_task_day_performance(vault: Store) -> None:
    def fill(doc: NoteDoc) -> bool:
        for i in range(500):
            doc.add_task(f"task {i}")
        return True

    vault.mutate(D0, fill)
    doc = vault.read_doc(D0)
    assert len(doc.tasks) == 500
