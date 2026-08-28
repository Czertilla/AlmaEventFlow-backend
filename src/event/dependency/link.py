from typing import Annotated

from fastapi import Depends

from event.uow.link import LinkUOW

from ._uow import UOWDep

LinkUOWDep = Annotated[LinkUOW, Depends(UOWDep(LinkUOW))]
