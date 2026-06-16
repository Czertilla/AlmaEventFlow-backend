from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.calendar import CalendarUOW


CalendarUOWDep = Annotated[CalendarUOW, Depends(UOWDep(CalendarUOW))]
