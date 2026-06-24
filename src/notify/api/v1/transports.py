from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import auth_responses

from notify.schema.transport import TransportInfo
from notify.transport import registry

router = APIRouter(prefix="/transports", tags=["notify"])


@router.get("", responses={**auth_responses()})
async def list_transports(user: ActiveUserJWTDep) -> list[TransportInfo]:
    """Available transports with metadata for the control panel."""
    return [
        TransportInfo(
            type=transport.type,
            label=transport.label,
            requires_client=transport.requires_client,
            delegated=transport.delegated,
            available=transport.is_available(),
        )
        for transport in registry.all_transports()
    ]
