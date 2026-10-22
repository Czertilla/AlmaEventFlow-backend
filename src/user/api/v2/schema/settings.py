import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from user.dto.settings import UserSettingsPatchDTO

KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
MAX_PATCH_KEYS = 64


class UserSettingsRead(FromDTOMixinV1, BaseModel):
    values: dict[str, Any] = Field(
        description="Client settings by name; the client owns the names and the values."
    )
    revision: int = Field(
        description="Grows with every change; 0 while nothing was ever saved."
    )
    edited_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UserSettingsPatch(ToDTOMixinV1, BaseModel):
    __dto_cls__ = UserSettingsPatchDTO

    values: dict[str, Any] = Field(
        description=(
            "Settings to change by name; a null removes the setting, "
            "the settings left out stay as they are."
        ),
    )

    @field_validator("values")
    @classmethod
    def _check_keys(cls, values: dict[str, Any]) -> dict[str, Any]:
        if len(values) > MAX_PATCH_KEYS:
            raise ValueError(f"at most {MAX_PATCH_KEYS} settings per request")
        for key in values:
            if not KEY_PATTERN.match(key):
                raise ValueError(f"invalid setting name: {key!r}")
        return values
