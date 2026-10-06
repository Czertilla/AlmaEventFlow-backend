from bot.tg.dto.actor import ActorDTO
from bot.tg.enum.message import MessageArgs
from bot.tg.state.menu import MenuStateGroup
from bot.tg.utils.abstract.usecase import BotUseCase, InlineBuilderMixin


class MenuUseCase(BotUseCase, InlineBuilderMixin):
    @BotUseCase.required_state
    async def on_start(self, actor: ActorDTO) -> MessageArgs:
        await self.state.set_state(MenuStateGroup._)
        return MessageArgs(
            text=await self.text_builder.on_main(actor),
            reply_markup=await self.inline_builder.main_menu(actor),
        )

    async def on_help(self, actor: ActorDTO) -> MessageArgs:
        return MessageArgs(text=await self.text_builder.on_help(actor))

    @BotUseCase.required_state
    async def on_info(self) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Help._)
        return MessageArgs(
            text=await self.text_builder.on_info(),
            reply_markup=await self.inline_builder.back_only_kb(),
        )

    async def on_link(self, *, back: bool) -> MessageArgs:
        return MessageArgs(
            text=await self.text_builder.on_link_steps(),
            reply_markup=await self.inline_builder.link_kb(back=back),
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

    async def on_fallback(self, actor: ActorDTO) -> MessageArgs:
        return MessageArgs(
            text=await self.text_builder.on_fallback(),
            reply_markup=await self.inline_builder.main_menu(actor),
        )

    async def on_wip(self) -> MessageArgs:
        return MessageArgs(text=await self.text_builder.on_wip())
