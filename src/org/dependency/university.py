from typing import Annotated

from fastapi import Depends

from org.uow.university import UniversityUOW

from ._uow import UOWDep

UniversityUOWDep = Annotated[UniversityUOW, Depends(UOWDep(UniversityUOW))]
