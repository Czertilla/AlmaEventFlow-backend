from typing import Any
from uuid import uuid4

import pytest

from event.exc.event import (
    AttendanceNotExistsException,
    EventNotExistsException,
    LinkNotExistsException,
    MemberNotExistsException,
    ParticipationNotExistsException,
    RewardNotExistsException,
    RoleNotExistsException,
    StageNotExistsException,
)
from event.service.attendance import AttendanceService
from event.service.event import EventService
from event.service.link import LinkService
from event.service.member import MemberService
from event.service.participation import ParticipationService
from event.service.reward import RewardService
from event.service.role import RoleService
from event.service.stage import StageService


class EmptyRepo:
    async def get_by_id(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def update_one(self, *args: Any, **kwargs: Any) -> None:
        return None


class EmptySession:
    async def scalar(self, *args: Any, **kwargs: Any) -> None:
        return None


class EmptyUoW:
    attendances = events = links = members = EmptyRepo()
    participations = rewards = roles = stages = EmptyRepo()
    session = EmptySession()

    async def __aenter__(self) -> "EmptyUoW":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def is_transacting(self) -> bool:
        return True


MISSING = [
    (AttendanceService, AttendanceNotExistsException),
    (EventService, EventNotExistsException),
    (LinkService, LinkNotExistsException),
    (MemberService, MemberNotExistsException),
    (ParticipationService, ParticipationNotExistsException),
    (RewardService, RewardNotExistsException),
    (RoleService, RoleNotExistsException),
    (StageService, StageNotExistsException),
]


@pytest.mark.parametrize(("service", "exception"), MISSING)
async def test_read_of_a_missing_row_raises_not_exists(
    service: Any, exception: type[Exception]
) -> None:
    with pytest.raises(exception):
        await service(EmptyUoW()).read(uuid4())


@pytest.mark.parametrize(("service", "exception"), MISSING)
async def test_update_of_a_missing_row_raises_not_exists(
    service: Any, exception: type[Exception]
) -> None:
    with pytest.raises(exception):
        await service(EmptyUoW())._update(uuid4(), {})
