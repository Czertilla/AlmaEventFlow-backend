from uuid import UUID

from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import ChatBindingDTO, ChatInfoDTO
from bot.tg.enum.message import MessageArgs
from bot.tg.service.collective_chat import CollectiveChatService
from bot.tg.utils.abstract.usecase import BotUseCase, InlineBuilderMixin
from core.config.settings import settings


class LeaderUseCase(BotUseCase, InlineBuilderMixin):
    async def on_list(
        self, actor: ActorDTO, bound: set[UUID], *, back: bool = True
    ) -> MessageArgs:
        return MessageArgs(
            text=await self.text_builder.on_leader_list(actor),
            reply_markup=await self.inline_builder.leader_list_kb(
                actor, bound, back=back
            ),
        )

    async def on_card(
        self,
        actor: ActorDTO,
        collective_id: UUID,
        binding: ChatBindingDTO | None,
        info: ChatInfoDTO | None,
        bind_url: str,
    ) -> MessageArgs | None:
        collective = actor.led_collective(collective_id)
        if collective is None:
            return None
        default_lang = settings.LOCALIZATION_DEFAULT_LANG
        return MessageArgs(
            text=await self.text_builder.on_leader_card(
                collective.name, binding, info, default_lang
            ),
            reply_markup=await self.inline_builder.leader_card_kb(
                collective_id, binding, bind_url, default_lang
            ),
        )

    async def on_card_for(
        self,
        actor: ActorDTO,
        collective_id: UUID,
        chat_service: CollectiveChatService,
        bind_url: str,
    ) -> MessageArgs | None:
        if not actor.leads(collective_id):
            return None
        binding = await chat_service.get_binding_of_collective(collective_id)
        info = (
            await chat_service.describe_chat(binding.chat_id)
            if binding is not None
            else None
        )
        return await self.on_card(actor, collective_id, binding, info, bind_url)

    async def on_not_leader(self) -> MessageArgs:
        return MessageArgs(text=await self.text_builder.on_not_leader())
