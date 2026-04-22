from core.api.event.organization import get_organization_event_router
from event.service.organization import OrganizationService
from event.uow.organization import OrganizationUOW
from event.dependency._uow import UOWDep

router = get_organization_event_router(
    OrganizationService, UOWDep(OrganizationUOW)
)
