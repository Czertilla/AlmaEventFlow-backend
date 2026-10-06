from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol


class FieldRequirer(Protocol):
    def __call__[**P, R](self, func: Callable[P, R], /) -> Callable[P, R]: ...


def required_field(field: str) -> FieldRequirer:
    def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            instance: Any = args[0]
            if getattr(instance, field, None) is None:
                raise ValueError(f"{field} field is required")
            return func(*args, **kwargs)

        return wrapper

    return decorator
