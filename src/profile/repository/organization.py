from core.repository.organization import OrganizationBaseRepo

from profile.models.organization import OrganizationORM as Model


class OrganizationRepo(
    OrganizationBaseRepo[Model]
):
    model = Model
