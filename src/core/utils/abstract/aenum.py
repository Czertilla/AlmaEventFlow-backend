from enum import EnumMeta, Enum


class DefaultEnumMeta(EnumMeta):
    def __call__(cls, value=None, *args, **kwargs):
        if (value is None) and hasattr(cls, "__default__"):
            return next(
                member for member in cls if member.value == cls.__default__
            )
        return super().__call__(value, *args, **kwargs)


class AEnum(Enum, metaclass=DefaultEnumMeta):
    @classmethod
    def _missing_(cls, value):
        if hasattr(cls, "__default__"):
            return cls()
        return super()._missing_(value)
