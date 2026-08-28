from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.tg.dependency.usecase.menu import MenuStateUseCaseDep
from bot.tg.enum.callbacks import CBPrefix

router = Router(name="/")
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == CBPrefix.back)
async def main_menu(callback: CallbackQuery, usecase: MenuStateUseCaseDep):
    await callback.message.edit_text(**await anext(usecase.on_start()))
