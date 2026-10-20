from typing import cast

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import KeyboardBuilder

from bot.tg.text.builder.builder import TextBuilder


class ABCKeyboardBuilder[ButtonType: (InlineKeyboardButton, KeyboardButton)](
    KeyboardBuilder[ButtonType]
):
    text_builder: TextBuilder

    def inline(self) -> InlineKeyboardMarkup:
        return cast(InlineKeyboardMarkup, self.as_markup())
