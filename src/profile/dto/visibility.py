from dataclasses import dataclass
from profile.enum.audience import Audience


@dataclass(frozen=True, slots=True)
class VisibilityEntryDTO:
    key: str
    label: str
    configurable: bool
    audience_min: Audience
    audience_max: Audience
    audience_default: Audience
    audience: Audience
    is_default: bool


@dataclass(frozen=True, slots=True)
class VisibilityChangeDTO:
    audience: Audience
