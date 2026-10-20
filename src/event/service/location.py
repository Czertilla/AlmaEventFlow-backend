from logging import getLogger
from uuid import UUID

from core.service.base import required_transaction
from core.service.event.location import LocationEventService as BaseService
from event.dto.location import RecentLocationDTO
from event.uow.location import LocationUOW

logger = getLogger(__name__)


class LocationService(BaseService[LocationUOW]):
    @required_transaction
    async def _delete(self, location_id: UUID):
        await self.uow.locations.detach_events(location_id)
        await super()._delete(location_id)

    @required_transaction
    async def _recent(self, collective_id: UUID, limit: int) -> list[RecentLocationDTO]:
        rows = await self.uow.locations.recent_for_collective(collective_id, limit)
        return [RecentLocationDTO(location_id=i, used_at=at) for i, at in rows]

    async def recent(self, collective_id: UUID, limit: int) -> list[RecentLocationDTO]:
        async with self.uow:
            return await self._recent(collective_id, limit)
