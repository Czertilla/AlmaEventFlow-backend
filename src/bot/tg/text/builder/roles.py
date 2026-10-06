from html import escape

from bot.enum.locales import LocaleKey
from bot.tg.dto.actor import ActorDTO
from bot.tg.dto.collective_chat import CollectiveRefDTO
from bot.tg.utils.abstract.text_builder import ABCTextBuilder

MAX_NAMES = 5


def collective_names(items: tuple[CollectiveRefDTO, ...]) -> str:
    shown = ", ".join(escape(item.name, quote=False) for item in items[:MAX_NAMES])
    hidden = len(items) - MAX_NAMES
    return f"{shown} +{hidden}" if hidden > 0 else shown


class RolesMixin(ABCTextBuilder):
    async def roles_lines(self, actor: ActorDTO) -> list[str]:
        led_ids = {item.id for item in actor.led}
        members = tuple(i for i in actor.member_of if i.id not in led_ids)
        lines: list[str] = []
        if actor.led:
            lines.append(
                await self.get_phrase(
                    LocaleKey.Account.roles_leader,
                    collectives=collective_names(actor.led),
                )
            )
        if members:
            lines.append(
                await self.get_phrase(
                    LocaleKey.Account.roles_member,
                    collectives=collective_names(members),
                )
            )
        if not lines:
            key = (
                LocaleKey.Account.roles_none
                if actor.roles_known
                else LocaleKey.Account.roles_unknown
            )
            lines.append(await self.get_phrase(key))
        return lines
