from uuid import UUID
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, AuthenticationBackend

from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.models.user import UserORM
from user.utils.jwt import JwtStrategy


cookie_transport = CookieTransport(
    cookie_name=settings.AUTH_COOKIE_NAME,
    cookie_max_age=settings.AUTH_COOKIE_MAX_AGE,
)


def get_jwt_strategy() -> JwtStrategy:
    return JwtStrategy(
        secret=settings.USER_SECRET.get_secret_value(),
        lifetime_seconds=settings.AUTH_COOKIE_MAX_AGE,
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
