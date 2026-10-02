from typing import Any

import pytest
from _behavior import generate_behavior


@pytest.fixture(scope="session")
def behavior() -> dict[str, dict[str, Any]]:
    return generate_behavior()
