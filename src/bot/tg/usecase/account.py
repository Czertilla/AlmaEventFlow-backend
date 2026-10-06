from bot.tg.dto.actor import ActorDTO
from bot.tg.enum.message import MessageArgs
from bot.tg.state.menu import MenuStateGroup
from bot.tg.utils.abstract.usecase import BotUseCase, InlineBuilderMixin


class AccountUseCase(BotUseCase, InlineBuilderMixin):
    @BotUseCase.required_state
    async def on_account(
        self, actor: ActorDTO, notifications_enabled: bool | None = None
    ) -> MessageArgs:
        await self.state.set_state(MenuStateGroup.Account._)
        return MessageArgs(
            text=await self.text_builder.on_account(
                actor, notifications_enabled
            ),
            reply_markup=await self.inline_builder.account_kb(
                actor, notifications_enabled
            ),
        )

    @BotUseCase.required_state
    async def on_confirm_unlink(self) -> MessageArgs:
        return MessageArgs(
            text=await self.text_builder.on_confirm_unlink(),
            reply_markup=await self.inline_builder.account_unlink_confirm_kb(),
        )
