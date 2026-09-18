from fastapi import Depends

from core.broker.kafka import KafkaRouter
from core.broker.rpc import rpc_respond
from core.enum.rpc import EventRPC
from core.schema.error import ErrorCode
from core.schema.message.core import MQResponse
from core.schema.message.event import (
    AttendanceData,
    MyAttendanceRequest,
    MyAttendanceResponse,
    MyCollectiveData,
    MyCollectivesRequest,
    MyCollectivesResponse,
    PatchMyAttendanceRequest,
)
from core.utils.exc.http import VancedHTTPException
from event.dependency._uow import UOWDep
from event.exc.event import MemberNotExistsException
from event.schema.attendance import AttendancePatchData
from event.service.attendance import AttendanceService
from event.service.collective import CollectiveService
from event.uow.attendance import AttendanceUOW
from event.uow.collective import CollectiveUOW
from event.uow.member import MemberUOW

router = KafkaRouter()

CollectiveUOWDep = Depends(UOWDep(CollectiveUOW))
AttendanceUOWDep = Depends(UOWDep(AttendanceUOW))
MemberUOWDep = Depends(UOWDep(MemberUOW))


@router.subscriber(EventRPC.MY_COLLECTIVES)
async def on_my_collectives(
    request: MyCollectivesRequest, uow=CollectiveUOWDep
) -> MQResponse[MyCollectivesResponse]:
    async def _call() -> MyCollectivesResponse:
        collectives = await CollectiveService(uow).get_my_collectives(
            request.person_id
        )
        return MyCollectivesResponse(
            collectives=[
                MyCollectiveData.model_validate(c) for c in collectives
            ]
        )

    return await rpc_respond(_call())


@router.subscriber(EventRPC.MY_ATTENDANCE)
async def on_my_attendance(
    request: MyAttendanceRequest, uow=AttendanceUOWDep
) -> MQResponse[MyAttendanceResponse]:
    async def _call() -> MyAttendanceResponse:
        attendances = await AttendanceService(uow).get_mine_for_event(
            request.person_id, request.event_id
        )
        return MyAttendanceResponse(
            attendances=[AttendanceData.model_validate(a) for a in attendances]
        )

    return await rpc_respond(_call())


@router.subscriber(EventRPC.PATCH_MY_ATTENDANCE)
async def on_patch_my_attendance(
    request: PatchMyAttendanceRequest,
    member_uow=MemberUOWDep,
    attendance_uow=AttendanceUOWDep,
) -> MQResponse[AttendanceData]:
    async def _call() -> AttendanceData:
        async with member_uow as uow:
            member = await uow.members.get_by_id(request.member_id)
            if not member:
                raise MemberNotExistsException()
            if member.person_id != request.person_id:
                raise VancedHTTPException(
                    status_code=403, detail=ErrorCode.NOT_MEMBER_PERSON
                )
        attendance = await AttendanceService(attendance_uow).patch_mine(
            request.member_id,
            request.attendance_id,
            AttendancePatchData(is_attended=request.is_attended),
        )
        return AttendanceData.model_validate(attendance)

    return await rpc_respond(_call())
