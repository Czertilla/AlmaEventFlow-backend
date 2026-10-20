from collections.abc import Callable
from enum import Enum, EnumType, StrEnum
from typing import cast


def prefix[E: Enum](prefix: str) -> Callable[[type[E]], type[E]]:
    def decorator[C: Enum](enum_class: type[C], prefix: str = prefix) -> type[C]:
        if issubclass(enum_class, StrEnum):
            members: dict[str, str] = {}
            for name, member in enum_class.__members__.items():
                members[name] = prefix + member.value

            new_class = StrEnum(
                enum_class.__name__,
                members,
                module=enum_class.__module__,
            )
            new_class.__qualname__ = enum_class.__qualname__
            new_class.__doc__ = enum_class.__doc__
            return cast("type[C]", new_class)

        for attr in enum_class.__dict__.values():
            if hasattr(attr, "_value_") and isinstance(attr._value_, str):
                attr._value_ = prefix + attr._value_
            if isinstance(attr, EnumType):
                decorator(cast("type[Enum]", attr), prefix=prefix)
        return enum_class

    return decorator
