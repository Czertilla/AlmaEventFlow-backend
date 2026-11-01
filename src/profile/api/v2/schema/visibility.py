from profile.dto.visibility import VisibilityChangeDTO
from profile.enum.audience import Audience

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class VisibilitySetData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = VisibilityChangeDTO

    audience: Audience


class VisibilityEntryRead(FromDTOMixinV1, BaseModel):
    key: str
    label: str
    configurable: bool
    audience_min: Audience
    audience_max: Audience
    audience_default: Audience
    audience: Audience
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class VisibilityRead(BaseModel):
    items: list[VisibilityEntryRead]
