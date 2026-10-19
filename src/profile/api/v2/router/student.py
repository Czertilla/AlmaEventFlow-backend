from profile.api.v1.schema.student import (
    StudentPatch,
    StudentPatchData,
    StudentPut,
    StudentPutData,
    StudentRead,
)
from profile.dependency.student import StudentUOWDep
from profile.exc.user import NonPersonalUserException
from profile.service.student import StudentService

from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep, UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)

router = APIRouter(prefix="/students", tags=["student"])


@router.get(
    "/my",
    responses={
        **auth_responses(),
        **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED),
        **entity_not_found_responses("student"),
    },
)
async def get_my_student(user: ActiveUserJWTDep, uow: StudentUOWDep) -> StudentRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return StudentRead.from_dto(await StudentService(uow).read(user.person_id))


@router.put(
    "/my",
    responses={
        **auth_responses(),
        **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED),
        **entity_not_found_responses("profile"),
    },
)
async def put_my_student(
    student: StudentPutData, user: UserJWTDep, uow: StudentUOWDep
) -> StudentRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return StudentRead.from_dto(
        await StudentService(uow).put(
            StudentPut.model_validate(
                {"id": user.person_id, **student.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/my",
    responses={
        **auth_responses(),
        **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED),
        **entity_not_found_responses("student"),
    },
)
async def patch_my_student(
    student: StudentPatchData, user: UserJWTDep, uow: StudentUOWDep
) -> StudentRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return StudentRead.from_dto(
        await StudentService(uow).patch(
            StudentPatch.model_validate(
                {"id": user.person_id, **student.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def delete_my_student(user: UserJWTDep, uow: StudentUOWDep) -> None:
    if user.person_id is None:
        raise NonPersonalUserException()
    await StudentService(uow).delete(user.person_id)
