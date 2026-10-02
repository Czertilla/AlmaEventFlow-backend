import dataclasses
import datetime
import enum
import types
import typing
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from _examples import FIELD_OVERRIDES

_NONE_TYPE = type(None)


def value_for(tp: Any, path: str) -> Any:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        return value_for(next(a for a in args if a is not _NONE_TYPE), path)
    if origin is typing.Literal:
        return args[0]
    if origin in (list, set, frozenset):
        items: list[Any] = [value_for(args[0], path + "[]")]
        return cast("Any", origin)(items)
    if origin is dict:
        key = value_for(args[0], path + ".k")
        return {key: value_for(args[1], path + ".v")}
    if tp is typing.Any or tp is object:
        return "x"
    if isinstance(tp, type):
        cls = cast("type[Any]", tp)
        if issubclass(cls, enum.Enum):
            return next(iter(cls))
        if dataclasses.is_dataclass(cls):
            return dto_example(cls, path)
        if cls is bool:
            return True
        if cls is int:
            return 1
        if cls is float:
            return 1.5
        if cls is str:
            return FIELD_OVERRIDES.get(path.rsplit(".", 1)[-1], "x")
        if cls is datetime.datetime:
            return datetime.datetime(2026, 1, 1, 10, tzinfo=datetime.UTC)
        if cls is datetime.date:
            return datetime.date(2026, 1, 1)
        if cls is datetime.time:
            return datetime.time(10)
        if cls is UUID:
            return uuid5(NAMESPACE_URL, path)
    raise TypeError(f"no example for {tp!r} at {path}")


def dto_example(dto_cls: type, path: str | None = None) -> Any:
    path = path or dto_cls.__name__
    hints = typing.get_type_hints(dto_cls)
    kwargs = {
        f.name: value_for(hints[f.name], f"{path}.{f.name}")
        for f in dataclasses.fields(dto_cls)
        if f.init and f.name != "fields_set"
    }
    return dto_cls(**kwargs)
