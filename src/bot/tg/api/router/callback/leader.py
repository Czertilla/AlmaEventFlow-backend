from logging import getLogger
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from aiogram.utils.callback_answer import CallbackAnswer

from bot.enum.emoji import Emoji
from bot.enum.locales import Locale, LocaleKey
from bot.tg.dependency.actor import ActorDep
from bot.tg.dependency.usecase.leader import LeaderUseCaseDep
from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import ChatBindingDTO
from bot.tg.enum.callbacks import LeaderAction, LeaderCB
from bot.tg.schema.user import TGUser
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.usecase.leader import LeaderUseCase
from bot.tg.utils.deeplink import StartKind, encode_start, startgroup_url
from bot.tg.utils.html import html_escape
from bot.tg.utils.message import edit_message
from core.config.settings import settings

router = Router(name="leader/")
router.callback_query.filter(F.message.chat.type == "private")
logger = getLogger(__name__)

TOGGLES = {
    LeaderAction.announce: "announce_enabled",
    LeaderAction.silent: "silent",
    LeaderAction.pin: "pin_announcements",
}


def _next_language(binding: ChatBindingDTO) -> str:
    codes = [locale.value for locale in Locale]
    current = binding.language or settings.LOCALIZATION_DEFAULT_LANG
    index = codes.index(current) if current in codes else -1
    return codes[(index + 1) % len(codes)]


async def _show_card(
    callback: CallbackQuery,
    bot: Bot,
    usecase: LeaderUseCase,
    actor: ActorDTO,
    collective_id: UUID,
    service: CollectiveChatService,
) -> bool:
    args = await usecase.on_card_for(
        actor,
        collective_id,
        service,
        await startgroup_url(bot, encode_start(StartKind.bind, collective_id)),
    )
    if args is None:
        return False
    await edit_message(callback, args)
    return True


async def _show_list(
    callback: CallbackQuery,
    usecase: LeaderUseCase,
    actor: ActorDTO,
    service: CollectiveChatService,
) -> None:
    bound = await service.bindings_of([item.id for item in actor.led])
    await edit_message(callback, await usecase.on_list(actor, set(bound)))


async def _farewell(
    bot: Bot, binding: ChatBindingDTO, collective_name: str
) -> None:
    text = await TextBuilder(binding.language).get_phrase(
        LocaleKey.SetupChat.old_chat,
        ch=Emoji.information_source,
        collective=html_escape(collective_name),
    )
    try:
        await bot.send_message(
            binding.chat_id, text, message_thread_id=binding.thread_id
        )
    except TelegramAPIError:
        logger.info("could not tell chat %s it was unbound", binding.chat_id)


@router.callback_query(LeaderCB.filter())
async def leader(
    callback: CallbackQuery,
    callback_data: LeaderCB,
    callback_answer: CallbackAnswer,
    actor: ActorDep,
    user: TGUser,
    bot: Bot,
    usecase: LeaderUseCaseDep,
) -> None:
    text_builder = TextBuilder(lang=user.language_code)
    if not actor.is_leader or actor.person_id is None:
        callback_answer.text = await text_builder.on_not_leader()
        callback_answer.show_alert = True
        return
    service = CollectiveChatService(CollectiveChatUOW(), bot)
    action, collective_id = callback_data.action, callback_data.collective_id

    if action is LeaderAction.list or collective_id is None:
        await _show_list(callback, usecase, actor, service)
        return
    if not actor.leads(collective_id):
        callback_answer.text = await text_builder.on_leader_stale()
        callback_answer.show_alert = True
        await _show_list(callback, usecase, actor, service)
        return

    if action in TOGGLES:
        binding = await service.get_binding_of_collective(collective_id)
        if binding is not None:
            changed = await service.update_settings(
                actor.person_id,
                collective_id,
                {TOGGLES[action]: not getattr(binding, TOGGLES[action])},
            )
            callback_answer.text = await text_builder.get_phrase(
                LocaleKey.Leader.saved
            )
            logger.info(
                "collective %s setting %s -> %s",
                collective_id,
                action,
                changed is not None,
            )
    elif action is LeaderAction.language:
        binding = await service.get_binding_of_collective(collective_id)
        if binding is not None:
            await service.update_settings(
                actor.person_id,
                collective_id,
                {"language": _next_language(binding)},
            )
            callback_answer.text = await text_builder.get_phrase(
                LocaleKey.Leader.saved
            )
    elif action is LeaderAction.unbind:
        removed = await service.unbind_collective(actor.person_id, collective_id)
        if removed is None:
            callback_answer.text = await text_builder.get_phrase(
                LocaleKey.Leader.nothing_to_unbind
            )
        else:
            callback_answer.text = await text_builder.get_phrase(
                LocaleKey.Leader.unbound
            )
            collective = actor.led_collective(collective_id)
            await _farewell(bot, removed, collective.name if collective else "")
            await _show_list(callback, usecase, actor, service)
            return

    await _show_card(callback, bot, usecase, actor, collective_id, service)
