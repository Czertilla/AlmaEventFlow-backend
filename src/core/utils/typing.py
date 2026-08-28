import types
import typing
from typing import Any


def iter_union(tp: Any) -> typing.Iterator[Any]:
    """Yields each member type of a ``Union``/``X | Y`` type alias, or ``tp``
    itself if it isn't a union. Unwraps ``Annotated[...]`` first, since
    pydantic discriminated unions are typically expressed that way."""
    if typing.get_origin(tp) is typing.Annotated:
        tp = typing.get_args(tp)[0]
    origin = typing.get_origin(tp)
    if origin is typing.Union or origin is types.UnionType:
        yield from typing.get_args(tp)
    else:
        yield tp


def unwrap_literal(tp: Any) -> Any:
    """The sole value of a single-member ``Literal[...]`` annotation, or the
    tuple of values for a multi-member one. Returns ``tp`` unchanged if it
    isn't a ``Literal``."""
    if typing.get_origin(tp) is typing.Literal:
        args = typing.get_args(tp)
        return args[0] if len(args) == 1 else args
    return tp
