from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.text.builder.roles import RolesMixin


class MenuMixin(RolesMixin):
    async def on_main(self, actor: ActorDTO) -> str:
        if not actor.is_linked:
            return await self.get_phrase(LocaleKey.Menu.Main.welcome)
        lines = [
            await self.get_phrase(LocaleKey.Menu.Main.title),
            await self.get_phrase(LocaleKey.Account.connected),
            *await self.roles_lines(actor),
        ]
        return "\n".join(lines)

    async def on_link_steps(self) -> str:
        return await self.get_phrase(LocaleKey.Menu.Link.steps)

    async def on_help(self, actor: ActorDTO | None = None) -> str:
        blocks = [
            await self.get_phrase(LocaleKey.Help.title),
            await self.get_phrase(LocaleKey.Help.private),
        ]
        if actor is None or not actor.is_linked:
            blocks.append(await self.get_phrase(LocaleKey.Help.unlinked))
        else:
            blocks.append(await self.get_phrase(LocaleKey.Help.linked))
        if actor is not None and actor.is_leader:
            blocks.append(await self.get_phrase(LocaleKey.Help.leader))
        if actor is not None and actor.is_superuser:
            blocks.append(await self.get_phrase(LocaleKey.Help.superuser))
        head, *body = blocks
        commands = "\n".join(body)
        group = await self.get_phrase(LocaleKey.Help.group)
        return f"{head}\n\n{commands}\n\n{group}"

    async def on_info(self) -> str:
        return await self.get_phrase(LocaleKey.Menu.info)

    async def on_wip(self) -> str:
        return await self.get_phrase(LocaleKey.Error.wip, ch=Emoji.construction)

    async def on_fallback(self) -> str:
        return await self.get_phrase(LocaleKey.Fallback.private, ch=Emoji.eyes)

    async def on_edit_language(self, is_lang_modified: bool) -> str:
        return await self.get_phrase(
            LocaleKey.Menu.Language.title,
            current_lang=await self.get_phrase(
                LocaleKey.title
                if is_lang_modified
                else LocaleKey.Menu.Language.Items.sys,
                ch=Emoji.get_lang_emoji(self.lang)
                if is_lang_modified
                else Emoji.gear,
            ),
        )
