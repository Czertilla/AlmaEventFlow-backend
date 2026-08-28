from typing import Annotated

from fastapi import Depends

from notify.uow.notify import NotifyUOW

from ._uow import UOWDep

NotifyUOWDep = Annotated[NotifyUOW, Depends(UOWDep(NotifyUOW))]
