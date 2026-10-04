from typing import Any, ClassVar, Self

from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import model_validator

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

    @model_validator(mode="after")
    def _check_order_fields(self) -> Self:
        allowed = self.Constants.order_fields
        if not allowed:
            return self
        for entry in self.ordering_values or []:
            name = entry.lstrip("+-")
            if name not in allowed:
                raise ValueError(
                    f"{name} is not an allowed ordering field, "
                    f"use one of: {', '.join(allowed)}."
                )
        return self
