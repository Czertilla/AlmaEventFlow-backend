from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.link import LinkUOW


LinkUOWDep = Annotated[LinkUOW, Depends(UOWDep(LinkUOW))]
