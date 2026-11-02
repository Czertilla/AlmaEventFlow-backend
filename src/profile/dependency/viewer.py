from profile.dependency.account import CallerPersonDep
from profile.dto.access import ViewerDTO
from re import fullmatch
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request

from core.dependencies.auth import ActiveUserJWTDep

REQUEST_ID = r"[A-Za-z0-9._:-]{1,64}"


def http_request_id(request: Request) -> str:
    given = request.headers.get("x-request-id")
    if given is not None and fullmatch(REQUEST_ID, given):
        return given
    return uuid4().hex


async def get_viewer(
    request: Request, user: ActiveUserJWTDep, person_id: CallerPersonDep
) -> ViewerDTO:
    return ViewerDTO(
        user_id=user.id,
        person_id=person_id,
        is_superuser=user.is_superuser,
        http_request_id=http_request_id(request),
    )


ViewerDep = Annotated[ViewerDTO, Depends(get_viewer)]


async def get_account_viewer(request: Request, user: ActiveUserJWTDep) -> ViewerDTO:
    return ViewerDTO(
        user_id=user.id,
        person_id=None,
        is_superuser=user.is_superuser,
        http_request_id=http_request_id(request),
    )


AccountViewerDep = Annotated[ViewerDTO, Depends(get_account_viewer)]
