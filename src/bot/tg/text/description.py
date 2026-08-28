from functools import lru_cache
from logging import getLogger
from pathlib import Path
from typing import Generator

from core.utils.path import get_dir
from i18n.loaders.yaml_loader import Loader, YamlLoader

from bot.enum.locales import Locale

logger = getLogger(__name__)


def parse_locales(loader: Loader, filenames: list[str]) -> Generator[dict]:
    for filename in filenames:
        with open(Path() / "res/locales" / filename, "rb") as f:
            data = loader.parse_file(f)
        logger.debug(f"Got {data=} from {filename=}")
        yield data


def get_locales_data():
    loader = YamlLoader()
    logger.debug(f"Got loader {loader}")
    directory: list[str] = get_dir(Path() / "res/locales")
    logger.debug(f"Detected locales: {directory}")
    result = {}
    for part in parse_locales(loader, directory):
        result.update(part)
    logger.debug(f"Got {result=}")
    return result


@lru_cache
def get_bot_descriptions():
    result = []
    locales_data = get_locales_data()
    for locale in Locale:
        current: dict = locales_data.get(locale.value, {}).get(
            "description", ""
        )
        logger.debug(f"Got {current=}")
        result.append((current, locale))
    return result
