from core.api.event.person import get_person_event_router
from org.service.person import PersonService
from org.uow.person import PersonUOW
from org.dependency._uow import UOWDep

router = get_person_event_router(PersonService, UOWDep(PersonUOW))
