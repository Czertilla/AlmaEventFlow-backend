from typing import Annotated

from fastapi import Depends

from event.uow.attendance_change import AttendanceChangeUOW

from ._uow import UOWDep

AttendanceChangeUOWDep = Annotated[
    AttendanceChangeUOW, Depends(UOWDep(AttendanceChangeUOW))
]
