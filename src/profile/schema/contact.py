from profile.enum.contact import ContactType
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, PutUUIDMixinV1, UUIDMixinV1


class ContactItemCreate(BaseModel):
    type: ContactType
    value: str = Field(max_length=256)
    is_main: bool = False

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(ContactItemCreate):
    person_id: UUID


class ContactItemRead(ContactItemCreate, UUIDMixinV1): ...


class ContactRead(ContactItemRead):
    person_id: UUID


class ContactPatchData(PatchModelV1):
    type: ContactType | None = None
    value: str | None = Field(max_length=256, default=None)
    is_main: bool | None = None


class ContactPatch(ContactPatchData, UUIDMixinV1): ...


class ContactPutData(ContactCreate): ...


class ContactItemPutData(ContactItemCreate): ...


class ContactPut(ContactPutData, PutUUIDMixinV1): ...


class ContactItemPut(ContactItemPutData, PutUUIDMixinV1): ...
