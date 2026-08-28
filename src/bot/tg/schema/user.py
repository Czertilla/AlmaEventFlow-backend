from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from core.utils.mixin.pydantic import FromAttributes


class TGUser(BaseModel, FromAttributes):
    id: int
    user_id: UUID | None = None
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_superuser: bool | None = None

    _is_lang_modified: bool = False

    @model_validator(mode="after")
    def validate_language_code(self) -> Self:
        self._is_lang_modified = (
            self.language_code == self.language_code.upper()
        )
        self.language_code = self.language_code.lower()
        return self


class AdminViewUser(TGUser):
    created_at: datetime
    edited_at: datetime | None
