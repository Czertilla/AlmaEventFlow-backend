from uuid import UUID

from fastapi import Response

from user.config.settings import settings


REFRESH_COOKIE_PATH = "/user/v1/auth/jwt/refresh"
SESSION_COOKIE_PATH = "/"
"""The refresh token is confined to the refresh endpoint, so it never reaches
other routes. The session-id cookie carries no credential and is served on the
whole app so endpoints (e.g. the session manager) can identify the caller's own
session."""


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def unset_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def set_session_cookie(response: Response, session_id: UUID) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=str(session_id),
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=SESSION_COOKIE_PATH,
    )


def unset_session_cookie(response: Response) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=SESSION_COOKIE_PATH,
    )
