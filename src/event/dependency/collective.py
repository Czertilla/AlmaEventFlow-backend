from typing import Annotated

from fastapi import Depends

from event.uow.collective import CollectiveUOW

from ._uow import UOWDep

CollectiveUOWDep = Annotated[CollectiveUOW, Depends(UOWDep(CollectiveUOW))]
