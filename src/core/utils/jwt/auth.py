from logging import getLogger
from typing import Annotated, Optional
from uuid import UUID
import jwt

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, APIKeyCookie

from core.schema.user import UserJWT
from core.config.settings import settings
from core.utils.exc.http import VancedHTTPException


security = APIKeyCookie(name=settings.AUTH_COOKIE_NAME)
optional_security = APIKeyCookie(
    name=settings.AUTH_COOKIE_NAME, auto_error=False
)

logger = getLogger(__name__)


class JWTAuth:
    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        token_audience: Optional[list[str]] = None,
        active: bool = True,
        verified: bool = True,
        superuser: bool = False,
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.token_audience = token_audience or ["fastapi-users:auth"]
        self.active = active
        self.verified = verified
        self.superuser = superuser

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=self.token_audience if self.token_audience else None,
            )
            return payload
        except jwt.PyJWTError as exc:
            err_id = logger.error(
                "Invalid authentication credentials",
                exc_info=exc,
            )
            raise VancedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                err_id=err_id,
            )

    def verify_requires(self, user: UserJWT):
        if self.active > user.is_active:
            raise VancedHTTPException(status.HTTP_401_UNAUTHORIZED)
        elif (
            self.verified > user.is_verified
            or self.superuser > user.is_superuser
        ):
            raise VancedHTTPException(status.HTTP_403_FORBIDDEN)

    def extract_user_snapshot(self, token: str) -> UserJWT:
        payload = self.decode_token(token)

        return UserJWT(
            id=UUID(payload["sub"]),
            person_id=UUID(payload["per"]) if payload.get("per") else None,
            is_active=payload.get("act", True),
            is_verified=payload.get("ver", False),
            is_superuser=payload.get("sup", False),
        )

    def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> UserJWT:
        user = self.extract_user_snapshot(credentials)
        self.verify_requires(user)
        return user


class OptionalJWTAuth(JWTAuth):
    def __call__(
        self,
        credentials: Annotated[
            Optional[HTTPAuthorizationCredentials], Depends(optional_security)
        ],
    ) -> Optional[UserJWT]:
        if credentials is None:
            return None

        try:
            return self.extract_user_snapshot(credentials)
        except VancedHTTPException:
            return None


def create_jwt_auth(
    secret: str = settings.USER_SECRET.get_secret_value(),
    *,
    active: bool = True,
    verified: bool = True,
    superuser: bool = False,
) -> JWTAuth:
    return JWTAuth(
        secret=secret,
        active=active,
        verified=verified,
        superuser=superuser,
    )


def create_optional_jwt_auth(
    secret: str = settings.USER_SECRET.get_secret_value(),
) -> OptionalJWTAuth:
    return OptionalJWTAuth(secret=secret)
