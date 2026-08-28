from profile.dependency._uow import UOWDep
from profile.service.organization import OrganizationService
from profile.uow.organization import OrganizationUOW

from core.api.event.organization import get_organization_event_router

router = get_organization_event_router(
    OrganizationService, UOWDep(OrganizationUOW)
)
