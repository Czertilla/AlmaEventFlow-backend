from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.dependencies.uow import ModuleUOWDep
from core.enum.rpc import OrgRPC
from core.schema.message.core import MQResponse
from core.schema.message.org import (
    GetOrganizationRequest,
    OrganizationRef,
    ResolveFacultyRequest,
    ResolveOrganizationRequest,
    ResolveUniversityRequest,
)
from org.service.reference import ReferenceService
from org.uow.reference import ReferenceUOW

router = KafkaRouter()

ReferenceUOWDep = Depends(ModuleUOWDep("org")(ReferenceUOW))


@router.subscriber(OrgRPC.RESOLVE_UNIVERSITY)
async def on_resolve_university(
    request: ResolveUniversityRequest, uow: ReferenceUOW = ReferenceUOWDep
) -> MQResponse[OrganizationRef]:
    return await rpc_respond(ReferenceService(uow).university(request.name))


@router.subscriber(OrgRPC.RESOLVE_FACULTY)
async def on_resolve_faculty(
    request: ResolveFacultyRequest, uow: ReferenceUOW = ReferenceUOWDep
) -> MQResponse[OrganizationRef]:
    return await rpc_respond(
        ReferenceService(uow).faculty(request.name, request.university_id)
    )


@router.subscriber(OrgRPC.RESOLVE_ORGANIZATION)
async def on_resolve_organization(
    request: ResolveOrganizationRequest, uow: ReferenceUOW = ReferenceUOWDep
) -> MQResponse[OrganizationRef]:
    return await rpc_respond(ReferenceService(uow).organization(request.name))


@router.subscriber(OrgRPC.GET_ORGANIZATION)
async def on_get_organization(
    request: GetOrganizationRequest, uow: ReferenceUOW = ReferenceUOWDep
) -> MQResponse[OrganizationRef]:
    return await rpc_respond(ReferenceService(uow).get(request.id))
