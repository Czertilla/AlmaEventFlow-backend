from datetime import date
from profile.schema.diet import DietRead
from profile.schema.organization import OrganizationRead
from profile.schema.person import PersonRead
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1


class ProfileCreate(BaseModel, UUIDMixinV1):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileRead(ProfileCreate, UUIDMixinV1, TimestampMixinV1):
    person: PersonRead | None = None
    diet: DietRead | None = None
    workplace: OrganizationRead | None = None


class ProfilePatchData(PatchModelV1):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfilePatch(ProfilePatchData, UUIDMixinV1): ...


class ProfilePutData(ProfileCreate): ...


class ProfilePut(ProfilePutData, UUIDMixinV1): ...
