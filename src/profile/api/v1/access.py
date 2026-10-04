from uuid import UUID

from fastapi import status

from core.schema.error import ErrorCode
from core.schema.user import UserJWT
from core.utils.exc.http import VancedHTTPException


def ensure_self_or_superuser(user: UserJWT, person_id: UUID) -> None:
    if not user.is_superuser and user.person_id != person_id:
        raise VancedHTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ErrorCode.FORBIDDEN
        )
