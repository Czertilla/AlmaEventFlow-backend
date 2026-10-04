from typing import Annotated, Any

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from core.filter.depends import FilterDepends
from core.filter.ordered import OrderedFilter
from user.models.user import UserORM


class SampleFilter(OrderedFilter):
    order_by: list[str] | None = ["created_at"]

    class Constants(OrderedFilter.Constants):
        model = UserORM
        order_fields = ("created_at", "username")


def test_allowed_fields_are_accepted_with_either_direction() -> None:
    assert SampleFilter.model_validate(
        {"order_by": "-created_at,username"}
    ).order_by == [
        "-created_at",
        "username",
    ]


def test_fields_outside_the_allowlist_are_rejected_even_when_the_model_has_them() -> (
    None
):
    with pytest.raises(ValidationError, match="not an allowed ordering field"):
        SampleFilter.model_validate({"order_by": "hashed_password"})


def test_the_default_ordering_is_valid() -> None:
    assert SampleFilter().order_by == ["created_at"]


def test_the_allowed_fields_are_documented_on_the_parameter() -> None:
    description = SampleFilter.model_fields["order_by"].description

    assert description is not None
    assert "created_at, username" in description


def test_the_allowed_fields_reach_the_openapi_schema() -> None:
    app = FastAPI()

    @app.get("/items")
    async def items(  # pyright: ignore[reportUnusedFunction]
        _: Annotated[SampleFilter, FilterDepends(SampleFilter)],
    ) -> None: ...

    parameters: list[dict[str, Any]] = app.openapi()["paths"]["/items"]["get"][
        "parameters"
    ]
    order_by = next(item for item in parameters if item["name"] == "order_by")

    assert "created_at, username" in order_by["description"]
