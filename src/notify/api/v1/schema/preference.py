from pydantic import BaseModel, ConfigDict, Field

from core.enum.notify import TransportTypeEnum
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from notify.dto.preference import PreferenceItemDTO, PreferencesUpdateDTO


class PreferenceItem(BaseModel, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PreferenceItemDTO

    transport: TransportTypeEnum
    is_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class PreferencesRead(FromDTOMixinV1, BaseModel):
    preferences: list[PreferenceItem]


class PreferencesUpdate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = PreferencesUpdateDTO

    preferences: list[PreferenceItem] = Field(min_length=1)
