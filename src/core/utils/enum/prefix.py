from enum import EnumType

def prefix(prefix):
    def decorator(enum_class, prefix=prefix):
        for attr in enum_class.__dict__.values():
            if hasattr(attr, "_value_") and isinstance(attr._value_, str):
                attr._value_ = prefix + attr._value_
            if isinstance(attr, EnumType):
                decorator(attr, prefix=prefix)
        return enum_class

    return decorator

