from fastapi import APIRouter, Request

from core.schema.v1.health import HealthV1


def health_router(service: str) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health(request: Request) -> HealthV1:
        """Liveness probe: answers once the application has finished starting."""
        return HealthV1(service=service, version=request.app.version)

    return router
