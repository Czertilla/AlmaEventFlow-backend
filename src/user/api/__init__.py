from core.utils.broker.router import include_mq_routers
from core.broker.kafka import stream_router

from user.services.auth import fastapi_users, auth_backend
from user.services.oauth2 import google_oauth_client
from user.api.v1.verify import get_verify_router
from user.api.v1.check import router as check_router
from user.api.kafka.sub.person import router as person_router
from user.schemas.user import UserCreate, UserRead, UserUpdate
from user.config.settings import settings

from fastapi import APIRouter


def include_routers(app: APIRouter):
    include_mq_routers(app, stream_router, [person_router])

    app.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/v1/auth/jwt",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_users_router(
            UserRead, UserUpdate, requires_verification=True
        ),
        prefix="/v1/users",
        tags=["users"],
    )

    app.include_router(
        fastapi_users.get_verify_router(UserRead), prefix="/v1/auth", tags=["auth"]
    )

    app.include_router(
        get_verify_router(fastapi_users.get_user_manager, UserRead),
        prefix="/v1/auth",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_oauth_router(
            google_oauth_client,
            auth_backend,
            settings.OAUTH_STATE_SECRET.get_secret_value(),
            associate_by_email=True,
            is_verified_by_default=True,
        ),
        prefix="/v1/auth/google",
        tags=["auth"],
    )

    app.include_router(
        fastapi_users.get_oauth_associate_router(
            google_oauth_client,
            UserRead,
            settings.OAUTH_STATE_SECRET.get_secret_value(),
        ),
        prefix="/v1/auth/associate/google",
        tags=["auth"],
    )


    app.include_router(check_router)
