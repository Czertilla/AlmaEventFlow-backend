from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.diet import DietUOW


DietUOWDep = Annotated[DietUOW, Depends(UOWDep(DietUOW))]
