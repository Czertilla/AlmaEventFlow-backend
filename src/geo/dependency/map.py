from typing import Annotated

from fastapi import Depends

from geo.uow.map import MapUOW

from ._uow import UOWDep

MapUOWDep = Annotated[MapUOW, Depends(UOWDep(MapUOW))]
