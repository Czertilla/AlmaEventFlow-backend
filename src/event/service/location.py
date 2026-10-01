from logging import getLogger
from uuid import UUID

from sqlalchemy import update

from core.service.base import required_transaction
from core.service.event.location import LocationEventService as BaseService
from event.models.event import EventORM
from event.uow.location import LocationUOW

logger = getLogger(__name__)


class LocationService(BaseService[LocationUOW]):
    @required_transaction
    async def _delete(self, location_id: UUID):
        await self.uow.session.execute(
            update(EventORM)
            .where(EventORM.location_id == location_id)
            .values(location_id=None)
        )
        await super()._delete(location_id)
