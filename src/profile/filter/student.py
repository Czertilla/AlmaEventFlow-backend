from profile.dto.student import (
    StudentDegreeFilterDTO,
    StudentFilterDTO,
    StudentGroupFilterDTO,
)
from profile.models.person import PersonORM
from profile.models.student import StudentDegree, StudentGroupORM, StudentORM
from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class StudentFilter(
    RelatedSearchFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = StudentFilterDTO

    order_by: list[str] | None = ["student_id"]
    search: None | str = None
    group_id: int | None = None
    group_id__in: list[int] | None = None
    faculty_id: UUID | None = None
    faculty_id__isnull: bool | None = None
    is_active: bool | None = None
    is_budget: bool | None = None
    is_full: bool | None = None

    class Constants(RelatedSearchFilter.Constants):
        model = StudentORM
        search_model_fields = ["student_id"]
        search_relation = StudentORM.person
        search_related = (PersonORM.surname, PersonORM.name, PersonORM.patronymic)
        order_fields = (
            "student_id",
            "is_active",
            "is_budget",
            "is_full",
            "created_at",
            "edited_at",
        )


class StudentGroupFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentGroupFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    degree_id: int | None = None
    degree_id__in: list[int] | None = None
    faculty_id: UUID | None = None
    grade: int | None = None
    grade__in: list[int] | None = None

    class Constants(OrderedFilter.Constants):
        model = StudentGroupORM
        search_model_fields = ["name"]
        order_fields = ("name", "grade")


class StudentDegreeFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentDegreeFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(OrderedFilter.Constants):
        model = StudentDegree
        search_model_fields = ["name"]
        order_fields = ("name",)
