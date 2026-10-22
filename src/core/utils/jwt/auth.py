from logging import getLogger
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from core.config.settings import settings
from core.schema.error import ErrorCode
from core.schema.user import UserJWT
from core.utils.exc.http import VancedHTTPException
from core.utils.keys import read_key

logger = getLogger(__name__)


bearer_scheme = HTTPBearer(auto_error=False)


def _access_public_key() -> str:
    return read_key(settings.RSA_PUBLIC_KEY_PATH, "The public key of the access tokens")


async def get_token(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if bearer is None:
        raise VancedHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorCode.NOT_AUTHENTICATED,
        )
    return bearer.credentials


async def get_optional_token(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    if bearer is not None:
        return bearer.credentials
    return None


class JWTAuth:
    def __init__(
        self,
        secret: str,
        algorithm: str = "RS256",
        token_audience: list[str] | None = None,
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

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=self.token_audience if self.token_audience else None,
            )
            return payload
        except jwt.PyJWTError as exc:
            logger.error("Invalid authentication credentials", exc_info=exc)
            raise VancedHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorCode.INVALID_AUTHENTICATION_CREDENTIALS,
            ) from exc

    def verify_requires(self, user: UserJWT):
        if self.active > user.is_active:
            raise VancedHTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail=ErrorCode.NOT_AUTHENTICATED,
            )
        elif (
            self.verified > user.is_verified
            or self.superuser > user.is_superuser
        ):
            raise VancedHTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=ErrorCode.FORBIDDEN,
            )

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
        token: Annotated[str, Depends(get_token)],
    ) -> UserJWT:
        user = self.extract_user_snapshot(token)
        self.verify_requires(user)
        return user


class OptionalJWTAuth(JWTAuth):
    def __call__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        token: Annotated[str | None, Depends(get_optional_token)],
    ) -> UserJWT | None:
        if token is None:
            return None

        try:
            return self.extract_user_snapshot(token)
        except VancedHTTPException:
            return None


def create_jwt_auth(
    secret: str | None = None,
    *,
    algorithm: str = "RS256",
    active: bool = True,
    verified: bool = True,
    superuser: bool = False,
) -> JWTAuth:
    if secret is None:
        secret = _access_public_key()
    return JWTAuth(
        secret=secret,
        algorithm=algorithm,
        active=active,
        verified=verified,
        superuser=superuser,
    )


def create_optional_jwt_auth(
    secret: str | None = None,
    *,
    algorithm: str = "RS256",
) -> OptionalJWTAuth:
    if secret is None:
        secret = _access_public_key()
    return OptionalJWTAuth(secret=secret, algorithm=algorithm)
