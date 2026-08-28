from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from bot.tg.enum.callbacks import CBPrefix
from bot.tg.text.builder import TextBuilder

from .menu import MenuMixin


class InlineBuilder(MenuMixin, InlineKeyboardBuilder):
    def __init__(self, text_builder: TextBuilder, *args, **kwargs):
        """
        Custom inline keyboard builder with localization support.

        Args:
            text_builder (TextBuilder): An instance for getting
            localized phrases.
        """
        super().__init__(*args, **kwargs)
        self.text_builder = text_builder

    async def _back_button(
        self, target_callback: str = CBPrefix.back
    ) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=await self.text_builder.back_button(),
            callback_data=target_callback,
        )
