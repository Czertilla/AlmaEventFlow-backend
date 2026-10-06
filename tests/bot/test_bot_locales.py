import re
from collections.abc import Iterator
from enum import Enum, EnumType
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from bot.enum.locales import Locale, LocaleKey

LOCALES = Path(__file__).resolve().parents[2] / "res" / "locales"
ALLOWED_TAGS = {
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "a",
    "code",
    "pre",
    "blockquote",
    "tg-spoiler",
    "tg-emoji",
    "tg-time",
}


def _load(lang: str) -> dict[str, Any]:
    with open(LOCALES / f"HTML.{lang}.yml", encoding="utf-8") as stream:
        return yaml.safe_load(stream)[lang]


def _flatten(tree: dict[str, Any], prefix: str = "") -> Iterator[tuple[str, str]]:
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            yield from _flatten(cast(dict[str, Any], value), f"{path}.")
        else:
            yield path, str(value)


def _enum_paths(enum: type[Enum]) -> Iterator[str]:
    for member in enum:
        yield str(member.value)
    for attr in vars(enum).values():
        if isinstance(attr, EnumType) and issubclass(attr, Enum):
            yield from _enum_paths(attr)


class _Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unknown: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            self.unknown.add(tag)
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack and self.stack[-1] == tag, f"unbalanced </{tag}>"
        self.stack.pop()


@pytest.fixture(scope="module")
def phrases() -> dict[str, dict[str, str]]:
    return {
        locale.value: {
            path: text
            for path, text in _flatten(_load(locale.value))
            if not path.startswith("_")
        }
        for locale in Locale
    }


def test_every_language_defines_the_same_phrases(
    phrases: dict[str, dict[str, str]],
) -> None:
    assert set(phrases["en"]) == set(phrases["ru"])


def test_every_locale_key_has_a_phrase(phrases: dict[str, dict[str, str]]) -> None:
    keys = set(_enum_paths(LocaleKey))

    assert keys == set(phrases["en"])


def test_phrases_are_valid_telegram_html(phrases: dict[str, dict[str, str]]) -> None:
    for lang, tree in phrases.items():
        for path, text in tree.items():
            balance = _Balance()
            balance.feed(text)
            balance.close()
            assert not balance.stack, f"{lang}:{path} leaves {balance.stack} open"
            assert not balance.unknown, f"{lang}:{path} uses {balance.unknown}"


def test_placeholders_match_between_languages(
    phrases: dict[str, dict[str, str]],
) -> None:
    pattern = re.compile(r"%\{(\w+)\}")
    for path, text in phrases["en"].items():
        assert set(pattern.findall(text)) == set(
            pattern.findall(phrases["ru"][path])
        ), path


def test_bot_profile_texts_fit_telegram_limits() -> None:
    for locale in Locale:
        tree = _load(locale.value)
        assert 0 < len(tree["description"]) <= 512
        assert 0 < len(tree["short_description"]) <= 120


def test_command_menus_are_valid_in_every_language() -> None:
    command = re.compile(r"^[a-z0-9_]{1,32}$")
    for locale in Locale:
        for scope, commands in _load(locale.value)["_commands"].items():
            assert commands, scope
            for name, description in commands.items():
                assert command.match(name), f"{locale.value}:{scope}:{name}"
                assert 3 <= len(description) <= 256, f"{locale.value}:{scope}:{name}"


def test_command_sets_are_the_same_in_every_language() -> None:
    en, ru = _load("en")["_commands"], _load("ru")["_commands"]

    assert {scope: list(cmds) for scope, cmds in en.items()} == {
        scope: list(cmds) for scope, cmds in ru.items()
    }


def test_locale_enum_covers_every_language() -> None:
    assert {locale.value for locale in Locale} == {"en", "ru"}
    assert isinstance(Locale.en, Enum)
