from pathlib import Path

import pytest
from _examples import characterize_package
from _snapshot import assert_matches

GOLDEN = Path(__file__).resolve().parent / "golden"
PACKAGES = {
    "event_v1": "event.api.v1.schema",
    "event_v2": "event.api.v2.schema",
    "core_v1": "core.schema.v1",
}


@pytest.mark.parametrize("name", PACKAGES)
def test_versioned_schema_behavior_is_unchanged(name: str) -> None:
    behavior = characterize_package(PACKAGES[name])

    assert behavior, f"{PACKAGES[name]} has no schema models"
    assert_matches(GOLDEN / f"{name}.json", behavior, PACKAGES[name])
