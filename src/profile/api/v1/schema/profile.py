from datetime import date
from profile.api.v1.schema.diet import DietRead
from profile.api.v1.schema.organization import OrganizationRead
from profile.api.v1.schema.person import PersonRead
from profile.dto.profile import ProfileCreateDTO, ProfilePatchDTO, ProfilePutDTO
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1


class ProfileBase(BaseModel, UUIDMixinV1):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileCreate(ProfileBase, ToDTOMixinV1):
    __dto_cls__ = ProfileCreateDTO


class ProfileRead(FromDTOMixinV1, ProfileBase, UUIDMixinV1, TimestampMixinV1):
    person: PersonRead | None = None
    diet: DietRead | None = None
    workplace: OrganizationRead | None = None


class ProfilePatchData(PatchModelV1):
    birthdate: date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfilePatch(ProfilePatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = ProfilePatchDTO


class ProfilePutData(ProfileBase): ...


class ProfilePut(ProfilePutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = ProfilePutDTO
