from typing import Annotated

from fastapi import Depends

from event.uow.role import RoleUOW

from ._uow import UOWDep

RoleUOWDep = Annotated[RoleUOW, Depends(UOWDep(RoleUOW))]
