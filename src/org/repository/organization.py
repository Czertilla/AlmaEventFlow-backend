from core.database.sqlalchemy.mixins.repositories import SearchRepositoryMixin
from core.repository.organization import OrganizationBaseRepo
from org.models.organization import OrganizationORM as Model


class OrganizationRepo(
    OrganizationBaseRepo[Model], SearchRepositoryMixin[Model]
):
    model = Model
