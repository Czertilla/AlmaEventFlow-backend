import uuid

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import TimestampMixinV1
from user.dto.user import UserCreateDTO, UserUpdateDTO


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
                "person_id",
                "invite_token",
            },
        )


class UserRead(
    FromDTOMixinV1,
    CreateUpdateUserModel,
    schemas.BaseUser[uuid.UUID],
    TimestampMixinV1,
):
    username: str | None
    person_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(CreateUpdateUserModel, schemas.BaseUserCreate, ToDTOMixinV1):
    __dto_cls__ = UserCreateDTO

    username: str
    invite_token: str | None = None


class UserUpdate(CreateUpdateUserModel, schemas.BaseUserUpdate, ToDTOMixinV1):
    __dto_cls__ = UserUpdateDTO

    username: str | None = None
    current_password: str | None = None


class PersonLinkRequest(BaseModel):
    person_id: uuid.UUID


class LinkInviteData(BaseModel):
    token: str
