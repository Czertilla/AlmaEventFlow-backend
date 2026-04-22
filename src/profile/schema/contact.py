from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, PutUUIDMixin, UUIDMixin
from profile.enum.contact import ContactType


class ContactItemCreate(BaseModel):
    type: ContactType
    value: str = Field(max_length=256)
    is_main: bool = False

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(ContactItemCreate):
    person_id: UUID


class ContactItemRead(ContactItemCreate, UUIDMixin): ...


class ContactRead(ContactItemRead):
    person_id: UUID


class ContactPatchData(PatchModel):
    type: ContactType | None = None
    value: str | None = Field(max_length=256, default=None)
    is_main: bool | None = None


class ContactPatch(ContactPatchData, UUIDMixin): ...


class ContactPutData(ContactCreate): ...


class ContactItemPutData(ContactItemCreate): ...


class ContactPut(ContactPutData, PutUUIDMixin): ...


class ContactItemPut(ContactItemPutData, PutUUIDMixin): ...
