from aiogram import F, Router
from aiogram.types import Message

from bot.tg.dependency.actor import ActorDep
from bot.tg.dependency.usecase.menu import MenuStateUseCaseDep

router = Router(name="fallback/")
router.message.filter(F.chat.type == "private")


@router.message()
async def fallback(
    message: Message, actor: ActorDep, usecase: MenuStateUseCaseDep
) -> None:
    await message.answer(**await usecase.on_fallback(actor))
