from collections.abc import Collection
from profile.enum.audience import Audience
from typing import Protocol
from uuid import UUID


class AccessData(Protocol):
    async def unit_heads(self, among: Collection[UUID] | None) -> set[UUID]: ...

    async def stored_audiences(
        self, field_key: str, among: Collection[UUID] | None
    ) -> dict[UUID, Audience]: ...

    async def shared_subjects(
        self, viewer_person_id: UUID, among: Collection[UUID] | None
    ) -> set[UUID]: ...
