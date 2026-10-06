from hashlib import sha1
from logging import getLogger

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.tg.dto.actor import ActorDTO
from bot.tg.schema.user import TGUser
from bot.tg.service.actor import ActorService
from bot.tg.text.commands import private_scope_names, static_hints, user_hints
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.uow.user import UserUOW
from core.dependencies.redis import redis

logger = getLogger(__name__)

SIGNATURE_TTL_SECONDS = 30 * 24 * 3600


def _key(tgid: int) -> str:
    return f"tg:commands:{tgid}"


def _signature(actor: ActorDTO) -> str:
    return sha1(",".join(private_scope_names(actor)).encode()).hexdigest()


class CommandMenuService:
    """Keeps each private chat's ``/`` menu in step with who the user is:
    Telegram shows only the most specific scope that has commands, so every
    scope carries a complete list for its role."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def setup_static(self) -> None:
        for hint in static_hints():
            try:
                await self.bot.set_my_commands(**hint)
            except TelegramAPIError:
                logger.exception(
                    "failed to set commands for scope=%s language=%s",
                    hint["scope"],
                    hint["language_code"],
                )

    async def refresh(self, actor: ActorDTO) -> bool:
        """Applies the menu for ``actor``'s private chat unless it is already
        what Telegram has. Never raises: a stale menu must not break a reply."""
        signature = _signature(actor)
        try:
            cached = await redis.get(_key(actor.tg_id))
            if cached is not None and (
                cached.decode() if isinstance(cached, bytes) else cached
            ) == signature:
                return False
            for hint in user_hints(actor):
                await self.bot.set_my_commands(**hint)
            await redis.set(
                _key(actor.tg_id), signature, ex=SIGNATURE_TTL_SECONDS
            )
        except Exception:
            logger.warning(
                "could not refresh the command menu of %s",
                actor.tg_id,
                exc_info=True,
            )
            return False
        return True

    async def refresh_superusers(self) -> None:
        async with UserUOW() as uow:
            tg_ids = await uow.users.get_all_superusers_tg_id()
        service = ActorService(AccountLinkUOW())
        for tg_id in tg_ids:
            stub = TGUser(
                id=tg_id, is_bot=False, first_name="-", is_superuser=True
            )
            await self.refresh(await service.resolve(stub))
