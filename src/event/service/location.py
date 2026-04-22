from logging import getLogger

from core.service.event.location import LocationEventService as BaseService
from event.uow.location import LocationUOW

logger = getLogger(__name__)


class LocationService(BaseService[LocationUOW]): ...
