from logging import getLogger

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.callback_answer import CallbackAnswer

from bot.enum.locales import LocaleKey
from bot.tg.dependency.actor import ActorDep
from bot.tg.enum.callbacks import SetupAction, SetupCB
from bot.tg.schema.user import TGUser
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.uow.collective_chat import CollectiveChatUOW
from bot.tg.usecase.setup_chat import SetupChatUseCase
from bot.tg.utils.html import plain_text
from bot.tg.utils.message import source_message

router = Router(name="setup_chat/")
router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))

logger = getLogger(__name__)


@router.callback_query(SetupCB.filter())
async def setup_chat_pick(
    callback: CallbackQuery,
    callback_data: SetupCB,
    callback_answer: CallbackAnswer,
    actor: ActorDep,
    user: TGUser,
    bot: Bot,
) -> None:
    """A tap on one of the buttons ``/setup_chat`` offers. The tapper is judged
    on their own rights, so a button pressed by anyone but the leader the
    choice is meant for is simply refused."""
    text_builder = TextBuilder(lang=user.language_code)
    message = source_message(callback)
    if message is None:
        return
    if callback_data.action is SetupAction.cancel:
        callback_answer.text = await text_builder.get_phrase(
            LocaleKey.SetupChat.cancelled
        )
        await message.delete()
        return
    usecase = SetupChatUseCase(
        bot,
        CollectiveChatService(CollectiveChatUOW(), bot),
        text_builder,
    )
    thread_id = message.message_thread_id if message.is_topic_message else None
    reply = await usecase.setup(
        actor,
        chat_id=message.chat.id,
        thread_id=thread_id,
        collective_id=callback_data.collective_id,
        replace=callback_data.action is SetupAction.swap,
    )
    if reply.private:
        callback_answer.text = plain_text(reply.text)
        callback_answer.show_alert = True
        return
    await message.edit_text(reply.text, reply_markup=reply.markup)
