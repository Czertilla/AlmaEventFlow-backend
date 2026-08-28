from datetime import date
from profile.schema.diet import DietRead
from profile.schema.organization import OrganizationRead
from profile.schema.person import PersonRead
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.utils.mixin.pydantic import PatchModel, TimestampMixin, UUIDMixin


class ProfileCreate(BaseModel, UUIDMixin):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileRead(ProfileCreate, UUIDMixin, TimestampMixin):
    person: PersonRead | None = None
    diet: DietRead | None = None
    workplace: OrganizationRead | None = None


class ProfilePatchData(PatchModel):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfilePatch(ProfilePatchData, UUIDMixin): ...


class ProfilePutData(ProfileCreate): ...


class ProfilePut(ProfilePutData, UUIDMixin): ...
