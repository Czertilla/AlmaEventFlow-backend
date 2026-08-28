from typing import Generic

from aiogram.utils.keyboard import ButtonType, KeyboardBuilder

from bot.tg.text.builder.builder import TextBuilder


class ABCKeyboardBuilder(KeyboardBuilder[ButtonType], Generic[ButtonType]):
    text_builder: TextBuilder
