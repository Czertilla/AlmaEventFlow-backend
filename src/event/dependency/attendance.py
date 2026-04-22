from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.attendance import AttendanceUOW


AttendanceUOWDep = Annotated[AttendanceUOW, Depends(UOWDep(AttendanceUOW))]
