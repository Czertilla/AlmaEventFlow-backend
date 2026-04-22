from core.api.event.address import get_address_event_router
from org.service.address import AddressService
from org.uow.address import AddressUOW
from org.dependency._uow import UOWDep

router = get_address_event_router(AddressService, UOWDep(AddressUOW))
