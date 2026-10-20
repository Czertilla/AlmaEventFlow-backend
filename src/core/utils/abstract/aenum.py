from collections.abc import Iterable
from enum import Enum, EnumMeta
from typing import Any, cast


class DefaultEnumMeta(EnumMeta):
    __default__: Any

    def __call__(cls, value: Any = None, *args: Any, **kwargs: Any) -> Any:
        if (value is None) and hasattr(cls, "__default__"):
            members = cast("Iterable[Enum]", cls)
            return next(
                member for member in members if member.value == cls.__default__
            )
        return super().__call__(value, *args, **kwargs)


class AEnum(Enum, metaclass=DefaultEnumMeta):
    @classmethod
    def _missing_(cls, value: object) -> Any:
        if hasattr(cls, "__default__"):
            return cls()
        return super()._missing_(value)
