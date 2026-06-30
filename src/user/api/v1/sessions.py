from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses

from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.exceptions.user import SessionNotFound
from user.schemas.user import SessionRead
from user.services.user import UserService

logger = getLogger(__name__)

router = APIRouter(prefix="/v1/users/me/sessions", tags=["sessions"])


def _current_session_id(request: Request) -> UUID | None:
    """Caller's own session id, taken from the session cookie. Returns ``None``
    when the cookie is absent or malformed."""
    raw = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        logger.debug("Malformed session cookie ignored")
        return None


@router.get("", responses={**auth_responses()})
async def list_my_sessions(
    request: Request,
    user: UserJWTDep,
    user_service: UserService = Depends(get_user_service),
) -> list[SessionRead]:
    """Lists the current user's active sessions, flagging the one in use."""
    return await user_service.list_sessions(
        user.id, _current_session_id(request)
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**auth_responses()},
)
async def revoke_other_sessions(
    request: Request,
    user: UserJWTDep,
    user_service: UserService = Depends(get_user_service),
) -> None:
    """Revokes every session of the current user except the one in use."""
    await user_service.revoke_other_sessions(
        user.id, _current_session_id(request)
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**auth_responses()},
)
async def revoke_session(
    session_id: UUID,
    user: UserJWTDep,
    user_service: UserService = Depends(get_user_service),
) -> None:
    """Revokes a single session owned by the current user."""
    if not await user_service.revoke_session(user.id, session_id):
        raise SessionNotFound()
