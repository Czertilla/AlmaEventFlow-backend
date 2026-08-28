from typing import Annotated

from fastapi import Depends

from org.uow.faculty import FacultyUOW

from ._uow import UOWDep

FacultyUOWDep = Annotated[FacultyUOW, Depends(UOWDep(FacultyUOW))]
