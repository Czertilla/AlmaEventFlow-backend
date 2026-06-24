from pydantic import BaseModel, ConfigDict, Field

from core.enum.notify import TransportTypeEnum


class PreferenceItem(BaseModel):
    transport: TransportTypeEnum
    is_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class PreferencesRead(BaseModel):
    preferences: list[PreferenceItem]


class PreferencesUpdate(BaseModel):
    preferences: list[PreferenceItem] = Field(min_length=1)
