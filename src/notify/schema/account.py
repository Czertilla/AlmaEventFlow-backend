from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AccountRead(BaseModel):
    id: UUID
    email: EmailStr
    is_verified: bool = False
    locale: str | None = None

    model_config = ConfigDict(from_attributes=True)
