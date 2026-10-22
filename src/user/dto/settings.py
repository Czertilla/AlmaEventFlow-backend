from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UserSettingsDTO:
    values: dict[str, Any]
    revision: int
    edited_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSettingsPatchDTO:
    values: dict[str, Any]
