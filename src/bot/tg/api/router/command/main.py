from logging import getLogger

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.exc.user import InvalidLinkTokenException, LinkTokenExpiredException
from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.usecase.account import AccountStateUserUseCaseDep
from bot.tg.dependency.usecase.menu import MenuStateUseCaseDep
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.usecase.account import AccountUseCase

router = Router()
router.message.filter(F.chat.type == "private")
logger = getLogger(__name__)


@router.message(CommandStart())
async def start(
    message: Message,
    command: CommandObject,
    usecase: MenuStateUseCaseDep,
    user: TGUser,
    uow: AccountLinkUOWDep,
    state: FSMContext,
) -> None:
    if command.args:
        await _handle_link(message, command.args, user, uow, state)
        return
    async for args in usecase.on_start():
        await message.answer(**args)


@router.message(Command("help"))
async def help(message: Message, usecase: MenuStateUseCaseDep) -> None:
    await message.answer(**await usecase.on_help())


@router.message(Command("account"))
async def account(
    message: Message, usecase: AccountStateUserUseCaseDep
) -> None:
    await message.answer(**await usecase.on_account())


async def _handle_link(
    message: Message,
    token: str,
    user: TGUser,
    uow: AccountLinkUOWDep,
    state: FSMContext,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    try:
        updated = await AccountLinkService(uow).link(user.id, token)
    except LinkTokenExpiredException:
        logger.info(f"expired link token for tg user {user.id=}")
        await message.answer(text=await text_builder.on_link_expired())
        return
    except InvalidLinkTokenException:
        logger.info(f"invalid link token for tg user {user.id=}")
        await message.answer(text=await text_builder.on_link_invalid())
        return
    await message.answer(text=await text_builder.on_link_success())
    usecase = AccountUseCase(text_builder, user=updated, state=state)
    await message.answer(**await usecase.on_account())
