from profile.uow.student import StudentGroupUOW, StudentUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

StudentUOWDep = Annotated[StudentUOW, Depends(UOWDep(StudentUOW))]
StudentGroupUOWDep = Annotated[StudentGroupUOW, Depends(UOWDep(StudentGroupUOW))]
