from typing import AsyncGenerator

from bot.tg.enum.message import MessageArgs
from bot.tg.state.menu import MenuStateGroup
from bot.tg.utils.abstract.usecase import BotUseCase, InlineBuilderMixin


class MenuUseCase(BotUseCase, InlineBuilderMixin):
    @BotUseCase.required_state
    async def on_start(self) -> AsyncGenerator[MessageArgs]:
        await self.state.set_state(MenuStateGroup._)
        yield MessageArgs(
            text=await self.text_builder.on_start(),
            reply_markup=await self.inline_builder.main_menu(),
        )

    @BotUseCase.required_state
    async def on_help(self) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Help._)
        return MessageArgs(
            text=await self.text_builder.on_help(),
        )

    @BotUseCase.required_state
    async def on_info(self) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Help._)
        return MessageArgs(
            text=await self.text_builder.on_info(),
            reply_markup=await self.inline_builder.back_only_kb(),
        )

    @BotUseCase.required_state
    @BotUseCase.required_user
    async def language(self) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Settings.Language._)
        return MessageArgs(
            text=await self.text_builder.on_edit_language(
                self.user._is_lang_modified
            ),
            reply_markup=await self.inline_builder.language_kb(),
        )

    async def on_wip(self) -> MessageArgs:
        return MessageArgs(text=await self.text_builder.on_wip())
