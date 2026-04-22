from typing import Annotated
from fastapi import Depends
from ._uow import UOWDep
from org.uow.collective import CollectiveUOW

CollectiveUOWDep = Annotated[CollectiveUOW, Depends(UOWDep(CollectiveUOW))]
