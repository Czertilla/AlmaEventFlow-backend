from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.member import MemberFilterDTO
from event.models.member import MemberORM
from event.models.person import PersonORM


class MemberFilter(
    RelatedSearchFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = MemberFilterDTO

    order_by: list[str] | None = [
        "person__surname",
        "person__name",
        "person__patronymic",
    ]
    search: str | None = None
    is_active: bool = True
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None
    person_id: UUID | None = None
    person_id__in: list[UUID] | None = None

    class Constants(RelatedSearchFilter.Constants):
        model = MemberORM
        search_relation = MemberORM.person
        search_related = (PersonORM.surname, PersonORM.name, PersonORM.patronymic)
        order_fields = (
            "person__surname",
            "person__name",
            "person__patronymic",
            "is_active",
            "created_at",
            "edited_at",
        )

    def sort(self, query):
        if not self.ordering_values:
            return query

        joined_rels = set()

        for field_name in self.ordering_values:
            direction = Filter.Direction.asc
            if field_name.startswith("-"):
                direction = Filter.Direction.desc
            field_name = field_name.replace("-", "").replace("+", "")

            if "__" in field_name:
                parts = field_name.split("__")
                model = self.Constants.model
                for part in parts[:-1]:
                    rel = getattr(model, part)
                    if rel not in joined_rels:
                        query = query.join(rel)
                        joined_rels.add(rel)
                    model = rel.property.mapper.class_
                order_by_field = getattr(model, parts[-1])
            else:
                order_by_field = getattr(self.Constants.model, field_name)

            query = query.order_by(getattr(order_by_field, direction)())

        return query
