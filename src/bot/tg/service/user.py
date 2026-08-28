from logging import getLogger
from typing import Any, Callable

from aiogram.types import Message, Update
from aiogram.types.user import User as AiogramUser

from bot.tg.model.user import TGUserORM
from bot.tg.schema.user import TGUser
from bot.tg.uow.user import UserUOW
from core.service.base import BaseService

logger = getLogger(__name__)


class TelegramUserService(BaseService[UserUOW]):
    async def check_username(self, value: str) -> bool:
        async with self.uow:
            return await self.uow.users.check_username(value)

    @staticmethod
    def filt_user_data(user_data: dict) -> dict:
        logger.debug(f"filtering unnecessary attributes for {user_data=}")
        if f := "id" not in user_data:
            user_data["id"] = 0
        user_data = TGUser(**user_data).model_dump(exclude_unset=True)
        if f:
            user_data.pop("id")
        return user_data

    async def update_user(
        self,
        user: AiogramUser,
        update: Update,
        *,
        from_db_update: Callable[[TGUserORM], dict[str, Any]] = lambda user: {
            "id": user.id
        },
    ) -> TGUser | None:
        response: TGUser
        logger.debug(f"updating data for {user=}")
        async with self.uow:
            user_data: dict = user.model_dump()
            user_model = await self.uow.users.get_by_id(user.id)
            if isinstance(user_model, TGUserORM):
                logger.debug(f"data for {user=} already exists")
                user_data.update(from_db_update(user_model))
                user_data = self.filt_user_data(user_data)
                if user_model.language_code == user_model.language_code.upper():
                    user_data.pop("language_code")
                user_model = await self.uow.users.update_one(
                    user_model.id, user_data
                )
            elif isinstance(
                update.event, Message
            ) and update.event.text.startswith("/start"):
                logger.debug(f"data for {user=} not exists yet")
                user_data = self.filt_user_data(user_data)
                user_model = await self.uow.users.add_n_return(user_data)
            else:
                return
            response = TGUser.model_validate(user_model)
            await self.uow.commit(True)
        logger.debug(f"after update {user=} got {response=}")
        return response

    async def set_lang(
        self, user: TGUser, lang: str, is_default: bool = False
    ) -> TGUser:
        async with self.uow:
            user_model = await self.uow.users.get_by_id(user.id)
            user_model.language_code = lang if is_default else lang.upper()
            await self.uow.commit()
            return TGUser.model_validate(user_model)

    async def get_user(self, id: int) -> TGUser | None:
        async with self.uow:
            user_model = await self.uow.users.get_by_id(id)
            if not user_model:
                return None
            return TGUser.model_validate(user_model)

    async def search(
        self, query: str, limit: int | None = None, offset: int = 0
    ) -> list[TGUser]:
        async with self.uow as uow:
            if query.startswith("@"):
                query = query[1:]
                search_method = uow.users.search_by_username
            else:
                search_method = uow.users.search_by_name
            users = await search_method(query, limit, offset)
            return [TGUser.model_validate(model) for model in users]
