from aiogram.filters import Filter
from aiogram.types import CallbackQuery, InlineQuery, Message

from bot.tg.dependency.user import UpdatedUserDep

EventUnion = Message | CallbackQuery | InlineQuery


class SuperUserFilter(Filter):
    async def __call__(self, event: EventUnion, user: UpdatedUserDep) -> bool:
        return bool(user.is_superuser)
