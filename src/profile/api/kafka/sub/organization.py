from core.api.event.organization import get_organization_event_router
from profile.service.organization import OrganizationService
from profile.uow.organization import OrganizationUOW
from profile.dependency._uow import UOWDep

router = get_organization_event_router(
    OrganizationService, UOWDep(OrganizationUOW)
)
