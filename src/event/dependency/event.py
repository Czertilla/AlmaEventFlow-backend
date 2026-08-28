from typing import Annotated

from fastapi import Depends

from event.uow.event import EventUOW

from ._uow import UOWDep

EventUOWDep = Annotated[EventUOW, Depends(UOWDep(EventUOW))]
