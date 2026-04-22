from typing import Annotated
from fastapi import Depends
from ._uow import UOWDep
from org.uow.university import UniversityUOW

UniversityUOWDep = Annotated[UniversityUOW, Depends(UOWDep(UniversityUOW))]
