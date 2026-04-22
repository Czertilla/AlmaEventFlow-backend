from typing import Callable, Self


def required_field(field: str) -> Callable:
    def decorator(func: Callable):
        def wrapper(self: Self, *args, **kwargs):
            if getattr(self, field, None) is None:
                raise ValueError(f"{field} field is required")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
