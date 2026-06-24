from enum import EnumType, StrEnum


def prefix(prefix):
    def decorator(enum_class, prefix=prefix):
        if issubclass(enum_class, StrEnum):
            members: dict[str, str] = {}
            for name, member in enum_class.__members__.items():
                if isinstance(member.value, str):
                    members[name] = prefix + member.value
                else:
                    members[name] = member.value  # type: ignore[assignment]

            new_class = StrEnum(
                enum_class.__name__,
                members,  # type: ignore[arg-type]
                module=enum_class.__module__,
            )
            new_class.__qualname__ = enum_class.__qualname__
            new_class.__doc__ = enum_class.__doc__
            return new_class

        for attr in enum_class.__dict__.values():
            if hasattr(attr, "_value_") and isinstance(attr._value_, str):
                attr._value_ = prefix + attr._value_
            if isinstance(attr, EnumType):
                decorator(attr, prefix=prefix)
        return enum_class

    return decorator

