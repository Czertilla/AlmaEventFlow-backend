from profile.api.v1.schema.diet import DietRead
from profile.api.v1.schema.student import StudentDegreeRead, StudentGroupRead
from profile.api.v2.schema.reference import (
    DegreeReference,
    DietReference,
    FacultyReference,
    OrganizationRefRead,
    ReferenceName,
    StudentGroupReference,
)
from profile.dependency.reference import ReferenceUOWDep
from profile.service.reference import ReferenceService

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import ErrorCode, auth_responses, detail_404

router = APIRouter(tags=["reference"])


@router.post("/diets", responses={**auth_responses()})
async def resolve_diet(
    data: DietReference, user: UserJWTDep, uow: ReferenceUOWDep
) -> DietRead:
    """Finds the record by its name, whatever the case and spacing, or makes it.

    Every endpoint of this router works so: what several profiles share is
    looked up first and added only when it is missing.
    """
    return DietRead.from_dto(await ReferenceService(uow).diet(data.name))


@router.post("/student-degrees", responses={**auth_responses()})
async def resolve_student_degree(
    data: DegreeReference, user: UserJWTDep, uow: ReferenceUOWDep
) -> StudentDegreeRead:
    return StudentDegreeRead.from_dto(await ReferenceService(uow).degree(data.name))


@router.post(
    "/student-groups",
    responses={
        **auth_responses(),
        **detail_404(ErrorCode.STUDENT_DEGREE_NOT_FOUND),
    },
)
async def resolve_student_group(
    data: StudentGroupReference, user: UserJWTDep, uow: ReferenceUOWDep
) -> StudentGroupRead:
    """A group is the same one when its faculty and name are."""
    return StudentGroupRead.from_dto(
        await ReferenceService(uow).group(
            data.name, data.degree_id, data.faculty_id, data.grade
        )
    )


@router.post("/universities", responses={**auth_responses()})
async def resolve_university(
    data: ReferenceName, user: UserJWTDep, uow: ReferenceUOWDep
) -> OrganizationRefRead:
    return OrganizationRefRead.from_dto(
        await ReferenceService(uow).university(data.name)
    )


@router.post(
    "/faculties",
    responses={**auth_responses(), **detail_404(ErrorCode.UNIVERSITY_NOT_FOUND)},
)
async def resolve_faculty(
    data: FacultyReference, user: UserJWTDep, uow: ReferenceUOWDep
) -> OrganizationRefRead:
    """A faculty is the same one when its university and name are."""
    return OrganizationRefRead.from_dto(
        await ReferenceService(uow).faculty(data.name, data.university_id)
    )


@router.post("/organizations", responses={**auth_responses()})
async def resolve_organization(
    data: ReferenceName, user: UserJWTDep, uow: ReferenceUOWDep
) -> OrganizationRefRead:
    """For a workplace: an organization, or a university, with that name."""
    return OrganizationRefRead.from_dto(
        await ReferenceService(uow).organization(data.name)
    )
