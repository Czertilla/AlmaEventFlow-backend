from logging import getLogger
from profile.dto.reference import OrganizationRefDTO
from profile.exc.organization import OrganizationServiceUnavailable
from uuid import UUID

from core.broker.rpc import RpcError, rpc_call
from core.enum.rpc import OrgRPC
from core.schema.message.core import MQRequest
from core.schema.message.org import (
    GetOrganizationRequest,
    OrganizationRef,
    ResolveFacultyRequest,
    ResolveOrganizationRequest,
    ResolveUniversityRequest,
)
from core.utils.exc.http import VancedHTTPException

logger = getLogger(__name__)


async def _ask(topic: OrgRPC, request: MQRequest) -> OrganizationRefDTO:
    try:
        ref = await rpc_call(topic, request, OrganizationRef)
    except RpcError as exc:
        raise VancedHTTPException(
            status_code=exc.error.code, detail=exc.error.detail
        ) from exc
    except Exception as exc:
        logger.exception("The organization service did not answer %s", topic)
        raise OrganizationServiceUnavailable() from exc
    return OrganizationRefDTO(id=ref.id, name=ref.name, type=ref.type)


async def resolve_university(name: str) -> OrganizationRefDTO:
    return await _ask(OrgRPC.RESOLVE_UNIVERSITY, ResolveUniversityRequest(name=name))


async def resolve_faculty(name: str, university_id: UUID) -> OrganizationRefDTO:
    return await _ask(
        OrgRPC.RESOLVE_FACULTY,
        ResolveFacultyRequest(name=name, university_id=university_id),
    )


async def resolve_organization(name: str) -> OrganizationRefDTO:
    return await _ask(
        OrgRPC.RESOLVE_ORGANIZATION, ResolveOrganizationRequest(name=name)
    )


async def get_organization(organization_id: UUID) -> OrganizationRefDTO:
    return await _ask(
        OrgRPC.GET_ORGANIZATION, GetOrganizationRequest(id=organization_id)
    )
