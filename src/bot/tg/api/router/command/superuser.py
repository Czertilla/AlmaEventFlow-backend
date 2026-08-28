"""
Superuser command router.

Demonstrates the custom "superuser" command scope: only chats where
`user.is_superuser` is true get this command hint, and `SuperUserFilter`
blocks the handler for everyone else.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.tg.api.filter.roles import SuperUserFilter
from bot.tg.dependency.usecase.menu import MenuUseCaseDep

router = Router(name="superuser/")

router.message.filter(F.chat.type == "private")
router.message.filter(SuperUserFilter())


@router.message(Command("admin"))
async def admin_panel(message: Message, usecase: MenuUseCaseDep) -> None:
    await message.answer(**await usecase.on_wip())
