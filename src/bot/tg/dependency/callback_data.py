from typing import Callable, TypeVar

from aiogram.types import CallbackQuery
from aiogram3_di import Depends

T = TypeVar("T")


def Parse(parser: Callable[[str], T]) -> Depends:
    def dependency(event: CallbackQuery) -> T:
        return parser(event.data)

    return Depends(dependency)
