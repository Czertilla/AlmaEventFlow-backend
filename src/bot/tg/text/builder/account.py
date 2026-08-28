from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.utils.abstract.text_builder import ABCTextBuilder


class AccountMixin(ABCTextBuilder):
    async def on_account(self, is_linked: bool) -> str:
        key = (
            LocaleKey.Account.linked
            if is_linked
            else LocaleKey.Account.not_linked
        )
        return await self.get_phrase(
            key, ch=Emoji.white_check_mark if is_linked else Emoji.warning
        )

    async def on_confirm_unlink(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.confirm_unlink, ch=Emoji.warning
        )

    async def on_unlinked(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.unlinked, ch=Emoji.white_check_mark
        )

    async def on_link_success(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.linked_success, ch=Emoji.white_check_mark
        )

    async def on_link_invalid(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.link_invalid, ch=Emoji.warning
        )

    async def on_link_expired(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.link_expired, ch=Emoji.warning
        )

    async def on_notifications_toggled(self, is_enabled: bool) -> str:
        key = (
            LocaleKey.Account.notifications_on
            if is_enabled
            else LocaleKey.Account.notifications_off
        )
        return await self.get_phrase(
            key, ch=Emoji.white_check_mark if is_enabled else Emoji.no_entry
        )

    async def on_notifications_error(self) -> str:
        return await self.get_phrase(
            LocaleKey.Account.notifications_error, ch=Emoji.warning
        )
