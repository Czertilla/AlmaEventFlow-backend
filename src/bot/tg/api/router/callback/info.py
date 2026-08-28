from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.tg.dependency.usecase.menu import MenuStateUseCaseDep
from bot.tg.enum.callbacks import CBPrefix

router = Router(name="info/")
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == CBPrefix.info)
async def info(callback: CallbackQuery, usecase: MenuStateUseCaseDep):
    await callback.message.edit_text(**await usecase.on_info())
