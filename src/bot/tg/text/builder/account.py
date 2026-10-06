from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.text.builder.roles import RolesMixin


class AccountMixin(RolesMixin):
    async def on_account(
        self, actor: ActorDTO, notifications_enabled: bool | None = None
    ) -> str:
        if not actor.is_linked:
            return await self.get_phrase(
                LocaleKey.Account.not_linked, ch=Emoji.warning
            )
        lines = [
            await self.get_phrase(LocaleKey.Account.title),
            await self.get_phrase(LocaleKey.Account.connected),
        ]
        if notifications_enabled is not None:
            key = (
                LocaleKey.Account.notifications_state_on
                if notifications_enabled
                else LocaleKey.Account.notifications_state_off
            )
            lines.append(await self.get_phrase(key))
        lines.extend(await self.roles_lines(actor))
        return "\n".join(lines)

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
