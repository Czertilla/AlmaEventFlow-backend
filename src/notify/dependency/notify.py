from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from notify.uow.notify import NotifyUOW


NotifyUOWDep = Annotated[NotifyUOW, Depends(UOWDep(NotifyUOW))]
