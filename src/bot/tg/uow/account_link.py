from bot.repository.user import UserRepo as AefUserRepo
from bot.tg.repository.user import UserRepo as TgUserRepo
from bot.uow.base import BotUnitOfWork


class AccountLinkMixin:
    users: AefUserRepo
    tg_users: TgUserRepo


class AccountLinkUOW(BotUnitOfWork, AccountLinkMixin):
    """Combines the AEF-identity (``user``) and Telegram-profile (``tg.user``)
    repositories so linking/unlinking an account is one atomic transaction."""
