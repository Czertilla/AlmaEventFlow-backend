from pathlib import Path
from typing import Any

import pytest
from _registry import SCHEMA_PACKAGES
from _snapshot import assert_matches

GOLDEN = Path(__file__).resolve().parent / "golden"


@pytest.mark.parametrize("name", SCHEMA_PACKAGES)
def test_versioned_schema_behavior_is_unchanged(
    name: str, behavior: dict[str, dict[str, Any]]
) -> None:
    characterized = behavior["characterize"][name]

    assert characterized, f"{SCHEMA_PACKAGES[name]} has no schema models"
    assert_matches(GOLDEN / f"{name}.json", characterized, SCHEMA_PACKAGES[name])
