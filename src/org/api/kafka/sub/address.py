from core.api.event.address import get_address_event_router
from org.dependency._uow import UOWDep
from org.service.address import AddressService
from org.uow.address import AddressUOW

router = get_address_event_router(AddressService, UOWDep(AddressUOW))
