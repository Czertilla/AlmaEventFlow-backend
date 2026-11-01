from typing import Any
from uuid import UUID

from core.enum.rpc import EventRPC
from core.schema.message.event import (
    SharedCollectiveSubjectsRequest,
    SharedCollectiveSubjectsResponse,
)


class FakeEvent:
    def __init__(self) -> None:
        self.seen: dict[UUID, set[UUID]] = {}
        self.calls: list[SharedCollectiveSubjectsRequest] = []
        self.down = False

    def share(self, first: UUID, second: UUID) -> None:
        self.seen.setdefault(first, set()).add(second)
        self.seen.setdefault(second, set()).add(first)

    async def __call__(
        self,
        topic: EventRPC,
        request: SharedCollectiveSubjectsRequest,
        model: Any,
        **_: Any,
    ) -> SharedCollectiveSubjectsResponse:
        assert topic == EventRPC.SHARED_COLLECTIVE_SUBJECTS
        self.calls.append(request)
        if self.down:
            raise TimeoutError
        shared = set(self.seen.get(request.viewer_person_id, set()))
        if request.subject_ids is not None:
            shared &= set(request.subject_ids)
        return SharedCollectiveSubjectsResponse(person_ids=sorted(shared))
