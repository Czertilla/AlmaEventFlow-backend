import difflib
import json
import os
from pathlib import Path
from typing import Any

import pytest

UPDATE = os.environ.get("UPDATE_CONTRACTS") == "1"
MAX_DIFF_LINES = 120
REGENERATE_HINT = "UPDATE_CONTRACTS=1 pytest tests/contract"


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def diff_message(expected: str, actual: str) -> str:
    diff = list(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            "snapshot",
            "current",
            lineterm="",
        )
    )
    shown = "\n".join(diff[:MAX_DIFF_LINES])
    return f"{len(diff)} diff lines\n{shown}"


def assert_matches(path: Path, data: Any, what: str) -> None:
    actual = dump_json(data)
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    if not path.exists():
        pytest.fail(f"{what}: no snapshot at {path}; run {REGENERATE_HINT}")
    expected = path.read_text(encoding="utf-8")
    if actual != expected:
        pytest.fail(
            f"{what} changed, but a released version must stay identical: "
            f"add a new version, or regenerate with {REGENERATE_HINT} and "
            f"review the diff.\n{diff_message(expected, actual)}"
        )
