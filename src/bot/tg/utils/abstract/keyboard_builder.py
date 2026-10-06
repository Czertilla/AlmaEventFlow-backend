from typing import Generic, cast

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import ButtonType, KeyboardBuilder

from bot.tg.text.builder.builder import TextBuilder


class ABCKeyboardBuilder(KeyboardBuilder[ButtonType], Generic[ButtonType]):
    text_builder: TextBuilder

    def inline(self) -> InlineKeyboardMarkup:
        return cast(InlineKeyboardMarkup, self.as_markup())
