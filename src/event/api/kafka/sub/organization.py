from core.api.event.organization import get_organization_event_router
from event.dependency._uow import UOWDep
from event.service.organization import OrganizationService
from event.uow.organization import OrganizationUOW

router = get_organization_event_router(
    OrganizationService, UOWDep(OrganizationUOW)
)
