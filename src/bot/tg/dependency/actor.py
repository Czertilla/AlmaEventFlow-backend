from typing import Annotated

from aiogram3_di import Depends  # pyright: ignore[reportMissingTypeStubs]

from bot.tg.dto.actor import ActorDTO
from bot.tg.schema.user import TGUser
from bot.tg.service.actor import ActorService
from bot.tg.uow.account_link import AccountLinkUOW


async def get_actor(user: TGUser | None) -> ActorDTO:
    if user is None:
        return ActorDTO(tg_id=0)
    return await ActorService(AccountLinkUOW()).resolve(user)


ActorDep = Annotated[ActorDTO, Depends(get_actor)]
