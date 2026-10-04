from fastapi import APIRouter


def include_routers(app: APIRouter, prefix: str) -> None:
    from user.api.auth import fastapi_users, oauth_backend
    from user.api.oauth2 import google_oauth_client
    from user.api.v1.router.auth import router as auth_router
    from user.api.v1.router.check import router as check_router
    from user.api.v1.router.sessions import router as sessions_router
    from user.api.v1.router.telegram import router as telegram_router
    from user.api.v1.router.telegram_auth import router as telegram_auth_router
    from user.api.v1.router.verify import get_verify_router
    from user.api.v1.schema.user import UserCreate, UserRead, UserUpdate
    from user.config.settings import settings

    state_secret = settings.OAUTH_STATE_SECRET.get_secret_value()

    app.include_router(auth_router, prefix=f"{prefix}/v1/auth/jwt", tags=["auth"])
    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix=f"{prefix}/v1/auth",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix=f"{prefix}/v1/auth",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_users_router(
            UserRead, UserUpdate, requires_verification=True
        ),
        prefix=f"{prefix}/v1/users",
        tags=["users"],
    )
    app.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix=f"{prefix}/v1/auth",
        tags=["auth"],
    )
    app.include_router(
        get_verify_router(fastapi_users.get_user_manager, UserRead),
        prefix=f"{prefix}/v1/auth",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_oauth_router(
            google_oauth_client,
            oauth_backend,
            state_secret,
            associate_by_email=True,
            is_verified_by_default=True,
        ),
        prefix=f"{prefix}/v1/auth/google",
        tags=["auth"],
    )
    app.include_router(
        fastapi_users.get_oauth_associate_router(
            google_oauth_client, UserRead, state_secret
        ),
        prefix=f"{prefix}/v1/auth/associate/google",
        tags=["auth"],
    )
    app.include_router(sessions_router, prefix=prefix, tags=["sessions"])
    app.include_router(telegram_router, prefix=prefix, tags=["telegram"])
    app.include_router(telegram_auth_router, prefix=prefix, tags=["auth"])
    app.include_router(check_router, prefix=prefix)
