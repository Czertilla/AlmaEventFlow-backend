from logging import getLogger

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.exc.user import InvalidLinkTokenException, LinkTokenExpiredException
from bot.tg.dependency.account_link import AccountLinkUOWDep
from bot.tg.dependency.actor import ActorDep
from bot.tg.dependency.usecase.account import AccountStateUserUseCaseDep
from bot.tg.dependency.usecase.leader import LeaderUseCaseDep
from bot.tg.dependency.usecase.menu import (
    MenuStateUseCaseDep,
    MenuStateUserUseCaseDep,
)
from bot.tg.dto.actor import ActorDTO
from bot.tg.schema.user import TGUser
from bot.tg.service.account_link import AccountLinkService
from bot.tg.service.actor import ActorService
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.service.commands import CommandMenuService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.usecase.account import AccountUseCase
from bot.tg.utils.deeplink import (
    StartKind,
    encode_start,
    parse_start,
    startgroup_url,
)
from bot.tg.utils.notifications import notifications_state

router = Router()
router.message.filter(F.chat.type == "private")
logger = getLogger(__name__)

CELEBRATE_EFFECT_ID = "5046509860389126442"


@router.message(CommandStart(), flags={"chat_action": "typing"})
async def start(
    message: Message,
    command: CommandObject,
    user: TGUser,
    actor: ActorDep,
    bot: Bot,
    uow: AccountLinkUOWDep,
    state: FSMContext,
    usecase: MenuStateUseCaseDep,
    leader_usecase: LeaderUseCaseDep,
) -> None:
    payload = parse_start(command.args)
    if command.args and payload is None:
        actor = await _handle_link(message, command.args, user, actor, uow, state)
    elif payload is not None and payload.kind is StartKind.lead:
        collective_id = payload.collective_id
        args = (
            await leader_usecase.on_card_for(
                actor,
                collective_id,
                CollectiveChatService(CollectiveChatUOW(), bot),
                await startgroup_url(
                    bot, encode_start(StartKind.bind, collective_id)
                ),
            )
            if collective_id is not None
            else None
        )
        if args is not None:
            await CommandMenuService(bot).refresh(actor)
            await message.answer(**args)
            return
    await CommandMenuService(bot).refresh(actor)
    await message.answer(**await usecase.on_start(actor))


@router.message(Command("help"))
async def help(
    message: Message, actor: ActorDep, usecase: MenuStateUseCaseDep
) -> None:
    await message.answer(**await usecase.on_help(actor))


@router.message(Command("link"))
async def link(
    message: Message,
    actor: ActorDep,
    usecase: MenuStateUseCaseDep,
    account_usecase: AccountStateUserUseCaseDep,
) -> None:
    if actor.is_linked:
        await message.answer(**await account_usecase.on_account(actor, None))
        return
    await message.answer(**await usecase.on_link(back=False))


@router.message(Command("account"), flags={"chat_action": "typing"})
async def account(
    message: Message,
    actor: ActorDep,
    bot: Bot,
    usecase: AccountStateUserUseCaseDep,
) -> None:
    await CommandMenuService(bot).refresh(actor)
    await message.answer(
        **await usecase.on_account(actor, await notifications_state(actor))
    )


@router.message(Command("setup_chat"))
async def setup_chat_in_private(message: Message, user: TGUser) -> None:
    text = await TextBuilder(lang=user.language_code).get_phrase(
        LocaleKey.SetupChat.groups_only, ch=Emoji.information_source
    )
    await message.answer(text)


@router.message(Command("language"))
async def language(message: Message, usecase: MenuStateUserUseCaseDep) -> None:
    await message.answer(**await usecase.language())


@router.message(Command("collectives"), flags={"chat_action": "typing"})
async def collectives(
    message: Message,
    actor: ActorDep,
    bot: Bot,
    usecase: LeaderUseCaseDep,
    menu: MenuStateUseCaseDep,
) -> None:
    if not actor.is_linked:
        await message.answer(**await menu.on_link(back=False))
        return
    if not actor.is_leader:
        await message.answer(**await usecase.on_not_leader())
        return
    await CommandMenuService(bot).refresh(actor)
    bound = await CollectiveChatService(CollectiveChatUOW(), bot).bindings_of(
        [item.id for item in actor.led]
    )
    await message.answer(**await usecase.on_list(actor, set(bound), back=False))


async def _handle_link(
    message: Message,
    token: str,
    user: TGUser,
    actor: ActorDTO,
    uow: AccountLinkUOW,
    state: FSMContext,
) -> ActorDTO:
    text_builder = TextBuilder(lang=user.language_code)
    try:
        updated = await AccountLinkService(uow).link(user.id, token)
    except LinkTokenExpiredException:
        logger.info(f"expired link token for tg user {user.id=}")
        await message.answer(text=await text_builder.on_link_expired())
        return actor
    except InvalidLinkTokenException:
        logger.info(f"invalid link token for tg user {user.id=}")
        await message.answer(text=await text_builder.on_link_invalid())
        return actor
    refreshed = await ActorService(AccountLinkUOW()).resolve(updated)
    success = await text_builder.on_link_success()
    try:
        await message.answer(text=success, message_effect_id=CELEBRATE_EFFECT_ID)
    except TelegramBadRequest:
        await message.answer(text=success)
    usecase = AccountUseCase(text_builder, user=updated, state=state)
    await message.answer(
        **await usecase.on_account(
            refreshed, await notifications_state(refreshed)
        )
    )
    return refreshed
