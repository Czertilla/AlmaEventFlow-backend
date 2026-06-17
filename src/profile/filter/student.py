from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.student import StudentDegree, StudentGroupORM, StudentORM


class StudentFilter(Filter):
    order_by: list[str] | None = ["student_id"]
    search: None | str = None
    group_id: int | None = None
    faculty_id: UUID | None = None
    is_active: bool | None = None

    class Constants(Filter.Constants):
        model = StudentORM
        search_model_fields = ["student_id"]


class StudentGroupFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    degree_id: int | None = None
    faculty_id: UUID | None = None
    grade: int | None = None

    class Constants(Filter.Constants):
        model = StudentGroupORM
        search_model_fields = ["name"]


class StudentDegreeFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = StudentDegree
        search_model_fields = ["name"]
