from datetime import datetime
from profile.enum.account import PersonLinkAction
from uuid import UUID

from pydantic import BaseModel, Field

from core.enum.profile import PersonLinkSource
from core.schema.v1.mixin.dto import FromDTOMixinV1


class AccountLinkChangeRead(FromDTOMixinV1, BaseModel):
    id: UUID
    user_id: UUID = Field(description="The account whose link changed.")
    old_person_id: UUID | None = Field(
        description="The person the account stood for before, none when it had no one."
    )
    new_person_id: UUID | None = Field(
        description="The person the account stands for after, none when it has no one."
    )
    action: PersonLinkAction
    source: PersonLinkSource
    actor_id: UUID | None = Field(
        description="The account that made the change, none when the system did."
    )
    created_at: datetime
