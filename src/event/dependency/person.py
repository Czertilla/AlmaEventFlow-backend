from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.person import PersonUOW


PersonUOWDep = Annotated[PersonUOW, Depends(UOWDep(PersonUOW))]
