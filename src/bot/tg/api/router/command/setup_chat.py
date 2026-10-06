from logging import getLogger
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dependency.actor import ActorDep
from bot.tg.schema.user import TGUser
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.usecase.setup_chat import ChatReply, SetupChatUseCase
from bot.tg.utils.deeplink import StartKind, parse_start
from bot.tg.utils.reply import reply_to_sender

router = Router(name="setup_chat/")
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

logger = getLogger(__name__)

ANONYMOUS_ADMIN_ID = 1087968824


def topic_of(message: Message) -> int | None:
    return message.message_thread_id if message.is_topic_message else None


async def send_reply(message: Message, reply: ChatReply) -> None:
    if reply.private:
        await reply_to_sender(message, reply.text, reply_markup=reply.markup)
    else:
        await message.reply(reply.text, reply_markup=reply.markup)


def use_case(bot: Bot, user: TGUser) -> SetupChatUseCase:
    return SetupChatUseCase(
        bot,
        CollectiveChatService(CollectiveChatUOW(), bot),
        TextBuilder(lang=user.language_code),
    )


@router.message(
    Command("setup_chat"),
    F.sender_chat | (F.from_user.id == ANONYMOUS_ADMIN_ID),
)
async def anonymous_admin(message: Message) -> None:
    text = await TextBuilder().get_phrase(
        LocaleKey.SetupChat.anonymous, ch=Emoji.warning
    )
    await message.reply(text)


@router.message(Command("setup_chat"), flags={"chat_action": "typing"})
async def setup_chat(
    message: Message,
    command: CommandObject,
    actor: ActorDep,
    user: TGUser,
    bot: Bot,
) -> None:
    usecase = use_case(bot, user)
    arg = (command.args or "").strip()
    if arg.lower() == "off":
        reply = await usecase.off(actor, message.chat.id)
    elif arg.lower() == "status":
        reply = await usecase.status(actor, message.chat.id)
    else:
        collective_id: UUID | None = None
        if arg:
            try:
                collective_id = UUID(arg)
            except ValueError:
                text = await TextBuilder(lang=user.language_code).get_phrase(
                    LocaleKey.SetupChat.invalid_id, ch=Emoji.warning
                )
                await reply_to_sender(message, text)
                return
        reply = await usecase.setup(
            actor,
            chat_id=message.chat.id,
            thread_id=topic_of(message),
            collective_id=collective_id,
        )
    await send_reply(message, reply)


@router.message(CommandStart(), flags={"chat_action": "typing"})
async def start_in_group(
    message: Message,
    command: CommandObject,
    actor: ActorDep,
    user: TGUser,
    bot: Bot,
) -> None:
    payload = parse_start(command.args)
    if (
        payload is None
        or payload.kind is not StartKind.bind
        or payload.collective_id is None
    ):
        return
    reply = await use_case(bot, user).setup(
        actor,
        chat_id=message.chat.id,
        thread_id=topic_of(message),
        collective_id=payload.collective_id,
    )
    await send_reply(message, reply)
