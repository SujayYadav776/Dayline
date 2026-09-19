"""Pure mapper: a parsed Task -> the dict a QML delegate consumes.

No Qt here (keeps viewmodels thin and unit-testable).
"""

from __future__ import annotations

import re
from typing import Any

from dayline.core.model import Task

_CHIP_RE = re.compile(
    r"🔁[^⏳🛫✅🔁🔺⏫🔼⏬#]*|📅\s*\d{4}-\d{2}-\d{2}?"
    r"|⏳\s*\d{4}-\d{2}-\d{2}?|🛫\s*\d{4}-\d{2}-\d{2}?"
    r"|➕\s*\d{4}-\d{2}-\d{2}?|✅\s*\d{4}-\d{2}-\d{2}?"
)
_TAG_RE = re.compile(r"(?<!\S)#[^\s#]+")

_PRIORITY_UI_LABEL = {
    "HIGHEST": "high",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "LOWEST": "low",
}


def chips_of(body: str) -> list[str]:
    chips = [c.strip() for c in _CHIP_RE.findall(body)]
    chips += _TAG_RE.findall(body)
    return chips


def task_to_row(task: Task) -> dict[str, Any]:
    """Stable keys consumed by TaskRow.qml."""
    return {
        "description": task.description,
        "statusKind": task.kind.value,
        "priority": _PRIORITY_UI_LABEL.get(task.priority.name, "") if task.priority else "",
        "chips": chips_of(task.body),
        "indentLevel": task.visual_indent() // 4,
        "body": task.body,
        "taskKey": task.line_no,
    }
