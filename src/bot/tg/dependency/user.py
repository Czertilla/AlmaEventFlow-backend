from typing import Annotated

from aiogram3_di import Depends

from bot.tg.schema.user import TGUser


def get_updated_user(user: TGUser) -> TGUser:
    return user


UpdatedUserDep = Annotated[TGUser, Depends(get_updated_user)]
