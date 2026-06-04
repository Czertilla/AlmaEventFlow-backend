from uuid import UUID
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    BearerTransport,
    AuthenticationBackend,
)

from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.models.user import UserORM
from user.utils.jwt import AccessStrategy


bearer_transport = BearerTransport(tokenUrl="/user/v1/auth/jwt/login")


def get_jwt_strategy() -> AccessStrategy:
    return AccessStrategy(
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


auth_backend = AuthenticationBackend(
    name=settings.AUTH_BACKEND_NAME,
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

oauth_backend = AuthenticationBackend(
    name="oauth",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserORM, UUID](
    get_user_service,
    [auth_backend, oauth_backend],
)
