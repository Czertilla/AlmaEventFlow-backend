from typing import Any
from uuid import UUID

from pydantic import BaseModel

from core.enum.rpc import EventRPC
from core.schema.message.event import (
    CollectiveActiveMembersRequest,
    CollectiveActiveMembersResponse,
    CollectivePrincipalCheckRequest,
    CollectivePrincipalCheckResponse,
    SharedCollectiveSubjectsRequest,
    SharedCollectiveSubjectsResponse,
)


class FakeEvent:
    def __init__(self) -> None:
        self.seen: dict[UUID, set[UUID]] = {}
        self.calls: list[SharedCollectiveSubjectsRequest] = []
        self.requests: list[tuple[EventRPC, BaseModel]] = []
        self.leaders: dict[UUID, UUID] = {}
        self.names: dict[UUID, str] = {}
        self.unverified: set[UUID] = set()
        self.members: dict[UUID, set[UUID]] = {}
        self.down = False
        self.down_topics: set[EventRPC] = set()

    def share(self, first: UUID, second: UUID) -> None:
        self.seen.setdefault(first, set()).add(second)
        self.seen.setdefault(second, set()).add(first)

    def collective(
        self,
        collective_id: UUID,
        leader: UUID,
        members: set[UUID],
        *,
        name: str = "Ансамбль",
        verified: bool = True,
    ) -> None:
        self.leaders[collective_id] = leader
        self.names[collective_id] = name
        self.members[collective_id] = set(members)
        if not verified:
            self.unverified.add(collective_id)

    async def __call__(
        self, topic: EventRPC, request: BaseModel, model: Any, **_: Any
    ) -> BaseModel:
        self.requests.append((topic, request))
        if isinstance(request, SharedCollectiveSubjectsRequest):
            self.calls.append(request)
        if self.down or topic in self.down_topics:
            raise TimeoutError
        if isinstance(request, CollectivePrincipalCheckRequest):
            assert topic == EventRPC.COLLECTIVE_PRINCIPAL_CHECK
            collective = request.collective_id
            if self.leaders.get(collective) != request.person_id:
                return CollectivePrincipalCheckResponse(is_principal=False)
            return CollectivePrincipalCheckResponse(
                is_principal=True,
                name=self.names[collective],
                is_verified=collective not in self.unverified,
            )
        if isinstance(request, CollectiveActiveMembersRequest):
            assert topic == EventRPC.COLLECTIVE_ACTIVE_MEMBERS
            return CollectiveActiveMembersResponse(
                person_ids=sorted(self.members.get(request.collective_id, set()))
            )
        assert topic == EventRPC.SHARED_COLLECTIVE_SUBJECTS
        assert isinstance(request, SharedCollectiveSubjectsRequest)
        shared = set(self.seen.get(request.viewer_person_id, set()))
        if request.subject_ids is not None:
            shared &= set(request.subject_ids)
        return SharedCollectiveSubjectsResponse(person_ids=sorted(shared))
