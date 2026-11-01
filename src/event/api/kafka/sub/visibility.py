from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.enum.rpc import EventRPC
from core.schema.message.core import MQResponse
from core.schema.message.event import (
    SharedCollectiveSubjectsRequest,
    SharedCollectiveSubjectsResponse,
)
from event.dependency._uow import UOWDep
from event.service.visibility import VisibilityService
from event.uow.member import MemberUOW

router = KafkaRouter()

MemberUOWDep = Depends(UOWDep(MemberUOW))


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
