from uuid import UUID

from bot.schema.user import User
from bot.uow.user import UserUOW
from core.service.base import BaseService


class UserService(BaseService[UserUOW]):
    async def create(self) -> User:
        async with self.uow:
            model = await self.uow.users.add_n_return({})
            await self.uow.commit(True)
            return User.model_validate(model)

    async def get(self, user_id: UUID) -> User | None:
        async with self.uow:
            model = await self.uow.users.get_by_id(user_id)
            if not model:
                return None
            return User.model_validate(model)

    async def delete(self, user_id: UUID) -> None:
        async with self.uow:
            await self.uow.users.delete_one(user_id)
            await self.uow.commit()
