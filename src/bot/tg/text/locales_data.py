from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml

from core.utils.path import get_dir

LOCALES_DIR = Path() / "res" / "locales"


@lru_cache
def locales_data() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for filename in get_dir(LOCALES_DIR):
        with open(LOCALES_DIR / filename, "rb") as stream:
            data.update(cast(dict[str, dict[str, Any]], yaml.safe_load(stream)))
    return data
