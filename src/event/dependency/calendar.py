from typing import Annotated

from fastapi import Depends

from event.uow.calendar import CalendarUOW

from ._uow import UOWDep

CalendarUOWDep = Annotated[CalendarUOW, Depends(UOWDep(CalendarUOW))]
