from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.student import StudentUOW


StudentUOWDep = Annotated[StudentUOW, Depends(UOWDep(StudentUOW))]
