from typing import Annotated

from fastapi import Depends

from geo.uow.city import CityUOW

from ._uow import UOWDep

CityUOWDep = Annotated[CityUOW, Depends(UOWDep(CityUOW))]
