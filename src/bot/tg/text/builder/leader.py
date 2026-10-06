from html import escape

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import ChatBindingDTO, ChatInfoDTO
from bot.tg.utils.abstract.text_builder import ABCTextBuilder


class LeaderMixin(ABCTextBuilder):
    async def on_leader_list(self, actor: ActorDTO) -> str:
        key = (
            LocaleKey.Leader.list
            if actor.led
            else LocaleKey.Leader.list_empty
        )
        return await self.get_phrase(key)

    async def on_not_leader(self) -> str:
        return await self.get_phrase(LocaleKey.Leader.not_leader, ch=Emoji.warning)

    async def on_leader_stale(self) -> str:
        return await self.get_phrase(LocaleKey.Leader.stale, ch=Emoji.warning)

    async def on_leader_load_error(self) -> str:
        return await self.get_phrase(
            LocaleKey.Leader.load_error, ch=Emoji.warning
        )

    async def state_label(self, value: bool) -> str:
        return await self.get_phrase(
            LocaleKey.Leader.State.on if value else LocaleKey.Leader.State.off
        )

    async def lang_label(self, code: str) -> str:
        key = {
            "ru": LocaleKey.Leader.Lang.ru,
            "en": LocaleKey.Leader.Lang.en,
        }.get(code, LocaleKey.Leader.Lang.ru)
        return await self.get_phrase(key)

    async def on_leader_card(
        self,
        name: str,
        binding: ChatBindingDTO | None,
        info: ChatInfoDTO | None,
        default_lang: str,
    ) -> str:
        blocks = [
            await self.get_phrase(
                LocaleKey.Leader.card_title, name=escape(name, quote=False)
            )
        ]
        if binding is None:
            blocks.append(await self.get_phrase(LocaleKey.Leader.chat_none))
            blocks.append(await self.get_phrase(LocaleKey.Leader.bind_hint))
            return "\n\n".join(blocks)
        if info is None:
            blocks.append(await self.get_phrase(LocaleKey.Leader.chat_unavailable))
        else:
            title = escape(info.title or str(binding.chat_id), quote=False)
            chat_line = await self.get_phrase(
                LocaleKey.Leader.chat_bound, title=title
            )
            if binding.thread_id is not None:
                chat_line = await self.get_phrase(
                    LocaleKey.Leader.chat_topic, base=chat_line
                )
            blocks.append(chat_line)
            if not info.bot_is_admin:
                blocks.append(
                    await self.get_phrase(LocaleKey.Leader.chat_bot_not_admin)
                )
        blocks.append(
            await self.get_phrase(
                LocaleKey.Leader.settings,
                announce=await self.state_label(binding.announce_enabled),
                silent=await self.state_label(binding.silent),
                pin=await self.state_label(binding.pin_announcements),
                language=await self.lang_label(binding.language or default_lang),
            )
        )
        return "\n\n".join(blocks)
