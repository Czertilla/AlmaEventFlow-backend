from typing import Any, ClassVar

from sqlalchemy import or_

from core.filter.ordered import OrderedFilter


class RelatedSearchFilter(OrderedFilter):
    """``search`` matches the model's own ``search_model_fields`` and the
    ``search_related`` columns of the joined ``search_relation``."""

    search: str | None = None

    class Constants(OrderedFilter.Constants):
        search_relation: ClassVar[Any]
        search_related: ClassVar[tuple[Any, ...]] = ()

    def filter(self, query: Any) -> Any:
        term = self.search
        if term:
            pattern = f"%{term}%"
            own = [
                getattr(self.Constants.model, name).ilike(pattern)
                for name in getattr(self.Constants, "search_model_fields", [])
            ]
            related = [
                column.ilike(pattern) for column in self.Constants.search_related
            ]
            query = query.join(self.Constants.search_relation).where(
                or_(*own, *related)
            )
        self.search = None
        try:
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            self.search = term
