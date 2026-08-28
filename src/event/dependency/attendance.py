from typing import Annotated

from fastapi import Depends

from event.uow.attendance import AttendanceUOW

from ._uow import UOWDep

AttendanceUOWDep = Annotated[AttendanceUOW, Depends(UOWDep(AttendanceUOW))]
