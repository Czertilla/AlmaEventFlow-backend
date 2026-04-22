from logging import getLogger

from core.service.event.address import AddressEventService as BaseService

from org.uow.address import AddressUOW

logger = getLogger(__name__)


class AddressService(BaseService[AddressUOW]): ...
