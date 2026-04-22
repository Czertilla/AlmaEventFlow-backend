from org.models.organization import OrganizationORM as Model

from core.repository.organization import OrganizationBaseRepo


class OrganizationRepo(OrganizationBaseRepo[Model]):
    model = Model
