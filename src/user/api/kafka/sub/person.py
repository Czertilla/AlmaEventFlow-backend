from core.api.event.person import get_person_event_router
from user.service.person import UserPersonEventService
from user.uow.person import UserPersonUOW
from core.dependencies.uow import ModuleUOWDep

router = get_person_event_router(
    UserPersonEventService, ModuleUOWDep("user")(UserPersonUOW)
)
