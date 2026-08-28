from profile.uow.diet import DietUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

DietUOWDep = Annotated[DietUOW, Depends(UOWDep(DietUOW))]
