from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.tg.dependency.actor import ActorDep
from bot.tg.dependency.usecase.menu import MenuStateUseCaseDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.utils.message import edit_message

router = Router(name="/")
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == CBPrefix.back)
async def main_menu(
    callback: CallbackQuery, actor: ActorDep, usecase: MenuStateUseCaseDep
) -> None:
    await edit_message(callback, await usecase.on_start(actor))


@router.callback_query(F.data == CBPrefix.link)
async def link(callback: CallbackQuery, usecase: MenuStateUseCaseDep) -> None:
    await edit_message(callback, await usecase.on_link(back=True))
