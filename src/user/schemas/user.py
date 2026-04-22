from typing import Annotated, TypedDict
import uuid
from pydantic import BaseModel, ConfigDict, Field
from fastapi_users import schemas

class CreateUpdateUserModel(schemas.CreateUpdateDictModel):
    def create_update_dict(self):
        return self.model_dump(
            exclude_unset=True,
            exclude={
                "id",
                "is_superuser",
                "is_active",
                "is_verified",
                "oauth_accounts",
                "person_id"
            },
        )
    


class UserRead(CreateUpdateUserModel, schemas.BaseUser[uuid.UUID]):
    username: str
    person_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(CreateUpdateUserModel, schemas.BaseUserCreate):
    username: str


class UserUpdate(CreateUpdateUserModel, schemas.BaseUserUpdate):
    username: str


class UserOauthAccount(UserRead, schemas.BaseOAuthAccountMixin): ...


class SUser(UserOauthAccount): ...


class OAuthAccountDict(TypedDict):
    oauth_name: str
    access_token: str
    account_id: str
    account_email: str
    expires_at: int | None = None
    refresh_token: str | None = None


class CheckResponse(BaseModel):
    username: Annotated[str, Field(max_length=50)]
    exists: bool

    model_config = ConfigDict(from_attributes=True)
