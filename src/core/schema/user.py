from uuid import UUID
from pydantic import BaseModel


class UserJWT(BaseModel):
    id: UUID
    person_id: UUID | None = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
