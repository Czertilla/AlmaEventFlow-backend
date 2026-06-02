from uuid import UUID
from fastapi import Response
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    BearerTransport,
    CookieTransport,
    AuthenticationBackend,
)

from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.models.user import UserORM
from user.utils.jwt import AccessStrategy


cookie_transport = CookieTransport(
    cookie_name=settings.AUTH_COOKIE_NAME,
    cookie_max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    cookie_samesite=settings.AUTH_COOKIE_SAMESITE,
    cookie_secure=settings.AUTH_COOKIE_SECURE,
    cookie_domain=settings.AUTH_COOKIE_DOMAIN,
    cookie_httponly=True,
)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> AccessStrategy:
    return AccessStrategy(
        secret=settings.USER_SECRET.get_secret_value(),
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


auth_backend = AuthenticationBackend(
    name=settings.AUTH_BACKEND_NAME,
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserORM, UUID](
    get_user_service,
    [auth_backend],
)


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/",
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite="strict",
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="user/v1/auth/jwt",
    )


def unset_access_cookie(response: Response) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/",
    )


def unset_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        samesite="strict",
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/v1/auth/jwt",
    )
