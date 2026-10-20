from collections.abc import Callable
from typing import TypeVar

from aiogram.types import CallbackQuery
from aiogram3_di import Depends

T = TypeVar("T")


def Parse[T](parser: Callable[[str], T]) -> Depends:  # noqa: N802  # a DI factory named like a class
    def dependency(event: CallbackQuery) -> T:
        return parser(event.data)

    return Depends(dependency)
