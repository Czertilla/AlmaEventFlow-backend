from bot.tg.enum.message import MessageArgs
from bot.tg.state.menu import MenuStateGroup
from bot.tg.utils.abstract.usecase import BotUseCase, InlineBuilderMixin


class AccountUseCase(BotUseCase, InlineBuilderMixin):
    @BotUseCase.required_state
    @BotUseCase.required_user
    async def on_account(self) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Account._)
        is_linked = self.user.user_id is not None
        return MessageArgs(
            text=await self.text_builder.on_account(is_linked),
            reply_markup=await self.inline_builder.account_kb(is_linked),
        )

    @BotUseCase.required_state
    async def on_confirm_unlink(self) -> MessageArgs:
        return MessageArgs(
            text=await self.text_builder.on_confirm_unlink(),
            reply_markup=await self.inline_builder.account_unlink_confirm_kb(),
        )
