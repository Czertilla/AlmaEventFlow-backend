from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.tg.enum.message import MessageArgs


def inline_markup(args: MessageArgs) -> InlineKeyboardMarkup | None:
    markup = args.get("reply_markup")
    return markup if isinstance(markup, InlineKeyboardMarkup) else None


def source_message(callback: CallbackQuery) -> Message | None:
    message = callback.message
    return message if isinstance(message, Message) else None


async def edit_message(callback: CallbackQuery, args: MessageArgs) -> None:
    message = source_message(callback)
    if message is not None:
        await message.edit_text(
            text=args.get("text", ""), reply_markup=inline_markup(args)
        )
