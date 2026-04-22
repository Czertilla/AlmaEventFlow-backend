from core.repository.organization import OrganizationBaseRepo
from core.utils.abstract.unit_of_work import ABCUnitOfWork


class OrganizationAUOW(ABCUnitOfWork):
    organizations: OrganizationBaseRepo
