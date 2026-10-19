from typing import Any, ClassVar

from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field, ValidationInfo, field_validator
from pydantic.fields import FieldInfo
from sqlalchemy import or_

from core.filter.identity import id_search_clause

ORDER_HELP = (
    "Comma-separated fields, prefix a field with `-` for descending order. "
    "Allowed: {fields}."
)


def ordered(column: Any, descending: bool) -> Any:
    """A sort key that puts rows without a value last in both directions."""
    return (column.desc() if descending else column.asc()).nulls_last()


class OrderedFilter(Filter):
    """Sorts only by ``Constants.order_fields``; ``search`` also finds a row by id."""

    class Constants(Filter.Constants):
        order_fields: ClassVar[tuple[str, ...]] = ()

    def sort(self, query: Any) -> Any:
        entries: list[str] = self.ordering_values or []
        for entry in entries:
            column = getattr(self.Constants.model, entry.lstrip("+-"))
            query = query.order_by(ordered(column, entry.startswith("-")))
        return query

    def _search_clauses(self, term: str) -> list[Any]:
        model = self.Constants.model
        pattern = f"%{term}%"
        clauses: list[Any] = [
            getattr(model, name).ilike(pattern)
            for name in getattr(self.Constants, "search_model_fields", [])
        ]
        by_id = id_search_clause(model, term)
        if by_id is not None:
            clauses.append(by_id)
        return clauses

    def filter(self, query: Any) -> Any:
        name = self.Constants.search_field_name
        term = getattr(self, name, None)
        if term is not None:
            setattr(self, name, None)
        if term:
            clauses = self._search_clauses(term)
            if clauses:
                query = query.where(or_(*clauses))
        try:
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            if term is not None:
                setattr(self, name, term)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        allowed = cls.Constants.order_fields
        name = cls.Constants.ordering_field_name
        field = cls.model_fields.get(name)
        if allowed and field is not None and field.annotation is not None:
            cls.model_fields[name] = FieldInfo.from_annotated_attribute(
                field.annotation,
                Field(
                    default=field.default,
                    description=ORDER_HELP.format(fields=", ".join(allowed)),
                ),
            )
            cls.model_rebuild(force=True)

    @field_validator("*", mode="before", check_fields=False)
    def validate_order_by(cls, value: Any, field: ValidationInfo) -> Any:  # noqa: N805
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
