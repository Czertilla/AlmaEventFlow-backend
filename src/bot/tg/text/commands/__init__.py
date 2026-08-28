from logging import getLogger
from pathlib import Path
from typing import Generator

from aiogram.types import BotCommand
from core.utils.path import get_dir
from i18n.loaders.yaml_loader import Loader, YamlLoader

from bot.enum.locales import Locale
from bot.tg.text.commands.scopes import (
    BotCommandScope,
    CustomScope,
    get_custom_scopes,
    get_scope_types,
)

logger = getLogger(__name__)


def parse_locales(
    loader: Loader, filenames: list[str], push_commands: bool = True
) -> Generator[dict]:
    for filename in filenames:
        with open(
            Path() / "res" / "locales" / filename,
            "rb",
        ) as f:
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


async def get_commands_hints():
    scope_types = get_scope_types()

    args: dict[tuple[str, BotCommandScope], dict[str, str]] = {}
    locales_data = get_locales_data()
    for locale in Locale:
        current: dict = locales_data.get(locale.value, {}).get("_commands", {})
        logger.debug(f"Got {current=}")
        for scope, commands in current.items():
            if scope in CustomScope:
                args.update(
                    {
                        (key := (locale, sc)): args.get(key, {})
                        | commands
                        | current.get("default")
                        for sc in await get_custom_scopes(scope)
                    }
                )
                continue
            if scope not in scope_types.keys():
                logger.warning(f"{scope} - unknown scope has been ignored")
                continue
            args.update(
                {
                    (key := (locale, scope_types[scope]())): args.get(key, {})
                    | commands
                }
            )
            logger.debug(f"merge {commands=} under {key=}")
    logger.debug(f"Got {args=}")
    result = [
        {
            "language_code": key[0],
            "scope": key[1],
            "commands": [
                BotCommand(command=key1, description=val1)
                for key1, val1 in val.items()
            ],
        }
        for key, val in args.items()
    ]
    logger.debug(f"Got {result=}")
    return result
