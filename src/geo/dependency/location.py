from typing import Annotated

from fastapi import Depends

from geo.uow.location import LocationUOW

from ._uow import UOWDep

LocationUOWDep = Annotated[LocationUOW, Depends(UOWDep(LocationUOW))]
