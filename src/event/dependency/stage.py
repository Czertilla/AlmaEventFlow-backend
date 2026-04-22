from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.stage import StageUOW


StageUOWDep = Annotated[StageUOW, Depends(UOWDep(StageUOW))]
