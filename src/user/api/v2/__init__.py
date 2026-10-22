from fastapi import FastAPI


def include_routers(app: FastAPI, prefix: str) -> None:
    from user.api.v2.router.settings import router as settings_router

    app.include_router(settings_router, prefix=f"{prefix}/v2")
