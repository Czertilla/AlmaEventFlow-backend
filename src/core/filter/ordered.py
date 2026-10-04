from typing import Any, ClassVar

from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import ValidationInfo, field_validator

ORDER_HELP = (
    "Comma-separated fields, prefix a field with `-` for descending order. "
    "Allowed: {fields}."
)


class OrderedFilter(Filter):
    """A ``Filter`` that sorts only by the fields its ``Constants.order_fields``
    names, instead of any attribute of the model, and lists them in the
    ``order_by`` parameter's description."""

    class Constants(Filter.Constants):
        order_fields: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        allowed = cls.Constants.order_fields
        field = cls.model_fields.get(cls.Constants.ordering_field_name)
        if allowed and field is not None:
            field.description = ORDER_HELP.format(fields=", ".join(allowed))
            cls.model_rebuild(force=True)

    @field_validator("*", mode="before", check_fields=False)
    def validate_order_by(cls, value: Any, field: ValidationInfo) -> Any:
        if field.field_name != cls.Constants.ordering_field_name:
            return value
        if not value:
            return None
        allowed = cls.Constants.order_fields
        seen: set[str] = set()
        entries: list[str] = value
        for entry in entries:
            name = entry.lstrip("+-")
            if allowed and name not in allowed:
                raise ValueError(
                    f"{name} is not an allowed ordering field, "
                    f"use one of: {', '.join(allowed)}."
                )
            if name in seen:
                raise ValueError(f"{name} appears more than once in the ordering.")
            seen.add(name)
        return value
