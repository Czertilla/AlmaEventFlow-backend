from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.enum.rpc import EventRPC
from core.schema.message.core import MQResponse
from core.schema.message.event import (
    CollectiveActiveMembersRequest,
    CollectiveActiveMembersResponse,
    CollectivePrincipalCheckRequest,
    CollectivePrincipalCheckResponse,
    SharedCollectiveSubjectsRequest,
    SharedCollectiveSubjectsResponse,
)
from event.dependency._uow import UOWDep
from event.service.collective_access import CollectiveAccessService
from event.service.visibility import VisibilityService
from event.uow.collective_access import CollectiveAccessUOW
from event.uow.member import MemberUOW

router = KafkaRouter()

MemberUOWDep = Depends(UOWDep(MemberUOW))
CollectiveAccessUOWDep = Depends(UOWDep(CollectiveAccessUOW))


@router.subscriber(EventRPC.SHARED_COLLECTIVE_SUBJECTS)
async def on_shared_collective_subjects(
    request: SharedCollectiveSubjectsRequest, uow: MemberUOW = MemberUOWDep
) -> MQResponse[SharedCollectiveSubjectsResponse]:
    async def _call() -> SharedCollectiveSubjectsResponse:
        subjects = await VisibilityService(uow).shared_subjects(
            request.viewer_person_id, request.subject_ids
        )
        return SharedCollectiveSubjectsResponse(person_ids=sorted(subjects))

    return await rpc_respond(_call())


@router.subscriber(EventRPC.COLLECTIVE_PRINCIPAL_CHECK)
async def on_collective_principal_check(
    request: CollectivePrincipalCheckRequest,
    uow: CollectiveAccessUOW = CollectiveAccessUOWDep,
) -> MQResponse[CollectivePrincipalCheckResponse]:
    async def _call() -> CollectivePrincipalCheckResponse:
        found = await CollectiveAccessService(uow).principal_check(
            request.person_id, request.collective_id
        )
        return CollectivePrincipalCheckResponse(
            is_principal=found.is_principal,
            name=found.name,
            is_verified=found.is_verified,
        )

    return await rpc_respond(_call())


@router.subscriber(EventRPC.COLLECTIVE_ACTIVE_MEMBERS)
async def on_collective_active_members(
    request: CollectiveActiveMembersRequest,
    uow: CollectiveAccessUOW = CollectiveAccessUOWDep,
) -> MQResponse[CollectiveActiveMembersResponse]:
    async def _call() -> CollectiveActiveMembersResponse:
        members = await CollectiveAccessService(uow).active_members(
            request.collective_id
        )
        return CollectiveActiveMembersResponse(person_ids=sorted(members))

    return await rpc_respond(_call())
