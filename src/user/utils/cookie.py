from fastapi import Response

from user.config.settings import settings


REFRESH_COOKIE_PATH = "/user/v1/auth/jwt/refresh"


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
