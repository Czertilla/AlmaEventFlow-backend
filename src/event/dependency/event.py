from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.event import EventUOW


EventUOWDep = Annotated[EventUOW, Depends(UOWDep(EventUOW))]
