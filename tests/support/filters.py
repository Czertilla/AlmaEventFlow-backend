import dataclasses
import types
import typing
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def sample(annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in (typing.Union, types.UnionType):
        return sample(next(arg for arg in args if arg is not type(None)))
    if origin is list:
        return [sample(args[0])]
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is str:
        return "x"
    if annotation is date:
        return date(2026, 1, 1)
    if annotation is datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return next(iter(annotation))
    if annotation is UUID:
        return uuid4()
    raise TypeError(f"no sample for {annotation!r}")


def filter_cases(filter_cls: Any) -> list[Any]:
    cases: list[Any] = [filter_cls()]
    ordering = filter_cls.Constants.ordering_field_name
    allowed: tuple[str, ...] = getattr(filter_cls.Constants, "order_fields", ())
    for entry in allowed:
        cases.append(filter_cls(**{ordering: [entry]}))
        cases.append(filter_cls(**{ordering: [f"-{entry}"]}))
    for name, field in filter_cls.model_fields.items():
        if name != ordering:
            cases.append(filter_cls(**{name: sample(field.annotation)}))
    return cases


async def exercise_filter(
    sessionmaker: async_sessionmaker[AsyncSession], filter_cls: Any
) -> None:
    model = filter_cls.Constants.model
    async with sessionmaker() as session:
        for case in filter_cases(filter_cls):
            statement = case.filter(case.sort(select(model)))
            await session.execute(statement.limit(1))


def dto_field_names(filter_cls: Any) -> set[str]:
    return {f.name for f in dataclasses.fields(filter_cls.__dto_cls__)}


def assert_dto_parity(filter_cls: Any) -> None:
    assert set(filter_cls.model_fields) == dto_field_names(filter_cls), (
        f"{filter_cls.__name__} and {filter_cls.__dto_cls__.__name__} "
        "expose different fields"
    )


def assert_ordering_documented(filter_cls: Any) -> None:
    field = filter_cls.model_fields[filter_cls.Constants.ordering_field_name]
    assert field.description is not None
    for entry in filter_cls.Constants.order_fields:
        assert entry in field.description
