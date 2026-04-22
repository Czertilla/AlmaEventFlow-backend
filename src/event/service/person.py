from logging import getLogger

from core.service.event.person import PersonEventService as BaseService
from event.uow.person import PersonUOW

logger = getLogger(__name__)


class PersonService(BaseService[PersonUOW]): ...
