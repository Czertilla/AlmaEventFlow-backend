from core.api.event.location import get_location_event_router
from event.dependency._uow import UOWDep
from event.service.location import LocationService
from event.uow.location import LocationUOW

router = get_location_event_router(LocationService, UOWDep(LocationUOW))
