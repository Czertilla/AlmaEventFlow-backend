from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.role import RoleUOW


RoleUOWDep = Annotated[RoleUOW, Depends(UOWDep(RoleUOW))]
