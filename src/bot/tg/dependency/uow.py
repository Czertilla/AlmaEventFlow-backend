from typing import Annotated

from aiogram3_di import Depends

from bot.tg.uow.user import UserUOW

UserUOWDep = Annotated[UserUOW, Depends(UserUOW)]
