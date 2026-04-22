from core.api.event.person import get_person_event_router
from event.service.person import PersonService
from event.uow.person import PersonUOW
from event.dependency._uow import UOWDep

router = get_person_event_router(PersonService, UOWDep(PersonUOW))
