from typing import Any
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.filter.identity import IdentityFilterMixin
from core.filter.ordered import ordered
from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.member import MemberFilterDTO
from event.models.member import MemberORM
from event.models.person import PersonORM
from event.models.role import RoleORM

DERIVED_FILTERS = ("role_id", "role_id__in", "include_inactive", "is_active")


class MemberFilter(
    RelatedSearchFilter,
    TimestampFilterMixin,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = MemberFilterDTO

    order_by: list[str] | None = [
        "person__surname",
        "person__name",
        "person__patronymic",
    ]
    search: str | None = None
    is_active: bool = True
    include_inactive: bool = False
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None
    person_id: UUID | None = None
    person_id__in: list[UUID] | None = None
    role_id: UUID | None = None
    role_id__in: list[UUID] | None = None

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

    def filter(self, query: Any) -> Any:
        given = {name: getattr(self, name) for name in DERIVED_FILTERS}
        if given["role_id"] is not None:
            query = query.where(MemberORM.roles.any(RoleORM.id == given["role_id"]))
        if given["role_id__in"]:
            query = query.where(
                MemberORM.roles.any(RoleORM.id.in_(given["role_id__in"]))
            )
        self.role_id = None
        self.role_id__in = None
        self.include_inactive = None  # pyright: ignore[reportAttributeAccessIssue]
        if given["include_inactive"]:
            self.is_active = None  # pyright: ignore[reportAttributeAccessIssue]
        try:
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            for name, value in given.items():
                setattr(self, name, value)

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

            query = query.order_by(
                ordered(order_by_field, direction == Filter.Direction.desc)
            )

        return query
