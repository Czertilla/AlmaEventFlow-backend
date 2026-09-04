from fastapi import APIRouter

from core.broker.kafka import stream_router
from core.utils.broker.router import include_mq_routers
from user.api.kafka.sub.person import router as person_router
from user.api.kafka.sub.telegram import router as telegram_rpc_router
from user.api.v1.auth import router as auth_router
from user.api.v1.check import router as check_router
from user.api.v1.sessions import router as sessions_router
from user.api.v1.telegram import router as telegram_router
from user.api.v1.telegram_auth import router as telegram_auth_router
from user.api.v1.verify import get_verify_router
from user.config.settings import settings
from user.schemas.user import UserCreate, UserRead, UserUpdate
from user.services.auth import auth_backend, fastapi_users, oauth_backend
from user.services.oauth2 import google_oauth_client

PREFIX = "/user"


def include_routers(app: APIRouter):
    include_mq_routers(app, stream_router, [person_router, telegram_rpc_router])

    app.include_router(
        auth_router,
        prefix=f"{PREFIX}/v1/auth/jwt",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix=f"{PREFIX}/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix=f"{PREFIX}/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_users_router(
            UserRead, UserUpdate, requires_verification=True
        ),
        prefix=f"{PREFIX}/v1/users",
        tags=["users"],
    )

    app.include_router(
        fastapi_users.get_verify_router(UserRead), prefix=f"{PREFIX}/v1/auth", tags=["auth"]
    )

    app.include_router(
        get_verify_router(fastapi_users.get_user_manager, UserRead),
        prefix=f"{PREFIX}/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_oauth_router(
            google_oauth_client,
            oauth_backend,
            settings.OAUTH_STATE_SECRET.get_secret_value(),
            associate_by_email=True,
            is_verified_by_default=True,
        ),
        prefix=f"{PREFIX}/v1/auth/google",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_oauth_associate_router(
            google_oauth_client,
            UserRead,
            settings.OAUTH_STATE_SECRET.get_secret_value(),
        ),
        prefix=f"{PREFIX}/v1/auth/associate/google",
        tags=["auth"],
    )


    app.include_router(sessions_router, prefix=PREFIX, tags=["sessions"])

    app.include_router(telegram_router, prefix=PREFIX, tags=["telegram"])

    app.include_router(telegram_auth_router, prefix=PREFIX, tags=["auth"])

    app.include_router(check_router, prefix=PREFIX)
