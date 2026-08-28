from logging import getLogger
from uuid import UUID

from bot.exc.user import InvalidLinkTokenException, LinkTokenExpiredException
from bot.tg.schema.user import TGUser
from bot.tg.uow.account_link import AccountLinkUOW
from bot.tg.utils.aef_client import (
    deregister_notify_client,
    deregister_oauth_link,
    register_notify_client,
    register_oauth_link,
)
from core.dependencies.redis import redis
from core.service.base import BaseService
from core.utils.telegram_link import TELEGRAM_LINK_REDIS_PREFIX

logger = getLogger(__name__)


class AccountLinkService(BaseService[AccountLinkUOW]):
    """Links/unlinks a Telegram profile to an AlmaEventFlow identity. The link
    code is minted by ``user``-service and stashed in Redis (Telegram's deep-link
    ``start`` parameter is capped at 64 ``[A-Za-z0-9_-]`` characters, too short
    for a signed token) — consumed here exactly once."""

    @staticmethod
    async def _resolve(code: str) -> UUID:
        raw = await redis.getdel(f"{TELEGRAM_LINK_REDIS_PREFIX}{code}")
        if raw is None:
            raise LinkTokenExpiredException()
        try:
            return UUID(raw.decode() if isinstance(raw, bytes) else raw)
        except (ValueError, TypeError, AttributeError):
            raise InvalidLinkTokenException()

    async def link(self, tgid: int, token: str) -> TGUser:
        person_id = await self._resolve(token)
        async with self.uow as uow:
            account = await uow.users.get_by_person_id(person_id)
            if account is None:
                account = await uow.users.add_n_return(
                    {"person_id": person_id}
                )
            else:
                # Re-linking a person already tied to another tgid replaces
                # that link (e.g. the user switched phones/accounts).
                await uow.tg_users.clear_link(account.id)
            tg_model = await uow.tg_users.update_one(
                tgid, {"user_id": account.id}
            )
            await uow.commit(True)
            logger.info(f"linked tg user {tgid=} to {person_id=}")
            result = TGUser.model_validate(tg_model)

        # Register the DM as a notify client outside the DB transaction (it's
        # an HTTP call). Best-effort: the link itself already succeeded, so a
        # transient failure here just means notifications don't go out yet.
        client_id = await register_notify_client(person_id, tgid)
        if client_id is not None:
            async with self.uow as uow:
                await uow.users.update_one(
                    account.id, {"notify_client_id": client_id}
                )
                await uow.commit(True)

        # Same best-effort treatment: sync into user-service's OAuthAccount
        # table so the website's Telegram Login Widget can find this link,
        # without letting a transient failure undo the link itself.
        await register_oauth_link(person_id, tgid, result.username)
        return result

    async def get_person_id(self, tgid: int) -> UUID | None:
        """Resolves the AEF ``person_id`` linked to this tgid, if any — used
        by handlers that need to act on the caller's behalf (e.g. the
        attendance buttons) but only have a raw Telegram user id."""
        async with self.uow as uow:
            tg_model = await uow.tg_users.get_by_id(tgid)
            if tg_model is None or tg_model.user_id is None:
                return None
            account = await uow.users.get_by_id(tg_model.user_id)
            return account.person_id if account else None

    async def unlink(self, tgid: int) -> TGUser | None:
        async with self.uow as uow:
            tg_model = await uow.tg_users.get_by_id(tgid)
            if tg_model is None:
                return None
            account = (
                await uow.users.get_by_id(tg_model.user_id)
                if tg_model.user_id is not None
                else None
            )
            if tg_model.user_id is not None:
                tg_model = await uow.tg_users.update_one(
                    tgid, {"user_id": None}
                )
            await uow.commit(True)
            logger.info(f"unlinked tg user {tgid=}")
            result = TGUser.model_validate(tg_model)

        if account is not None:
            if account.notify_client_id is not None:
                await deregister_notify_client(
                    account.person_id, account.notify_client_id
                )
            await deregister_oauth_link(account.person_id)
        return result
