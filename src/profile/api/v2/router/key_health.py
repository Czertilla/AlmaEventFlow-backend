from profile.api.v2.schema.health import KeyHealthRead
from profile.crypto import Health
from profile.service.key_health import key_provider_health

from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/keys",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": KeyHealthRead}},
)
async def get_key_health(response: Response) -> KeyHealthRead:
    """Whether personal data can be encrypted and decrypted now; `503` when a key
    provider does not answer. The liveness probe stays `/profile/v1/health`."""
    health = await key_provider_health()
    if health != Health.OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return KeyHealthRead(status=health)
