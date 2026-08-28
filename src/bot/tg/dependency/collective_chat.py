from typing import Annotated

from aiogram3_di import Depends

from bot.tg.uow.collective_chat import CollectiveChatUOW

CollectiveChatUOWDep = Annotated[
    CollectiveChatUOW, Depends(CollectiveChatUOW)
]
