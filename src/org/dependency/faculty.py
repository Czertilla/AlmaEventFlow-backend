from typing import Annotated
from fastapi import Depends
from ._uow import UOWDep
from org.uow.faculty import FacultyUOW

FacultyUOWDep = Annotated[FacultyUOW, Depends(UOWDep(FacultyUOW))]
