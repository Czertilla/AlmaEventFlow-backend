from dataclasses import dataclass
from profile.enum.audience import Audience
from profile.enum.value_kind import ValueKind


@dataclass(frozen=True, slots=True)
class Column:
    table: str
    column: str
    where: tuple[str, str] | None = None
    kind: ValueKind = "text"


@dataclass(frozen=True, slots=True)
class PersonalField:
    key: str
    label: str
    columns: tuple[Column, ...]
    audience_default: Audience
    audience_min: Audience
    audience_max: Audience
    audience_default_for_unit_head: Audience | None = None
    encrypted: bool = False
    grantable: bool = True
    blind_index: bool = False
    deprecated: bool = False

    @property
    def configurable(self) -> bool:
        return self.audience_min != self.audience_max

    @property
    def sensitive(self) -> bool:
        return self.audience_max == Audience.PRIVATE

    def default_for(self, *, unit_head: bool) -> Audience:
        if unit_head and self.audience_default_for_unit_head is not None:
            return self.audience_default_for_unit_head
        return self.audience_default
