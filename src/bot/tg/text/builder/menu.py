from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.utils.abstract.text_builder import ABCTextBuilder


class MenuMixin(ABCTextBuilder):
    async def on_start(self) -> str:
        return await self.get_phrase(LocaleKey.Start.greeting)

    async def on_help(self) -> str:
        return await self.get_phrase(LocaleKey.help)

    async def on_info(self) -> str:
        return await self.get_phrase(LocaleKey.Menu.info)

    async def on_wip(self) -> str:
        return await self.get_phrase(LocaleKey.Error.wip, ch=Emoji.construction)

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
