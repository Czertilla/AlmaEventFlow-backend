from typing import Any
from uuid import uuid4

import pytest

from event.exc.event import (
    AttendanceNotExistsException,
    LinkNotExistsException,
    MemberNotExistsException,
    RoleNotExistsException,
    StageNotExistsException,
)
from event.service.attendance import AttendanceService
from event.service.link import LinkService
from event.service.member import MemberService
from event.service.role import RoleService
from event.service.stage import StageService


class EmptyRepo:
    async def get_by_id(self, *args: Any, **kwargs: Any) -> None:
        return None


class EmptyUoW:
    attendances = links = members = roles = stages = EmptyRepo()

    async def __aenter__(self) -> "EmptyUoW":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def is_transacting(self) -> bool:
        return True


@pytest.mark.parametrize(
    ("service", "exception"),
    [
        (AttendanceService, AttendanceNotExistsException),
        (LinkService, LinkNotExistsException),
        (MemberService, MemberNotExistsException),
        (RoleService, RoleNotExistsException),
        (StageService, StageNotExistsException),
    ],
)
async def test_read_of_a_missing_row_raises_not_exists(
    service: Any, exception: type[Exception]
) -> None:
    with pytest.raises(exception):
        await service(EmptyUoW()).read(uuid4())
