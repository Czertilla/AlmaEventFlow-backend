from typing import Annotated

from aiogram3_di import Depends

from bot.tg.uow.account_link import AccountLinkUOW

AccountLinkUOWDep = Annotated[AccountLinkUOW, Depends(AccountLinkUOW)]
