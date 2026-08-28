from typing import Annotated

from fastapi import Depends

from event.uow.stage import StageUOW

from ._uow import UOWDep

StageUOWDep = Annotated[StageUOW, Depends(UOWDep(StageUOW))]
