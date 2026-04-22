from typing import Annotated
from fastapi import Depends
from ._uow import UOWDep
from geo.uow.location import LocationUOW

LocationUOWDep = Annotated[LocationUOW, Depends(UOWDep(LocationUOW))]
