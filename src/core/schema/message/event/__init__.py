from datetime import datetime
from uuid import UUID

from core.schema.message.core import MQRequest


class MyCollectivesRequest(MQRequest):
    person_id: UUID


class MyCollectiveData(MQRequest):
    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool


class MyCollectivesResponse(MQRequest):
    collectives: list[MyCollectiveData]


class MyAttendanceRequest(MQRequest):
    person_id: UUID
    event_id: UUID


class AttendanceData(MQRequest):
    id: UUID
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None
    is_verified: bool | None
    comment: str | None
    created_at: datetime
    edited_at: datetime | None


class MyAttendanceResponse(MQRequest):
    attendances: list[AttendanceData]


class PatchMyAttendanceRequest(MQRequest):
    person_id: UUID
    member_id: UUID
    attendance_id: UUID
    is_attended: bool
