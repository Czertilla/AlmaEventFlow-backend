from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from notify.uow.client import ClientUOW


ClientUOWDep = Annotated[ClientUOW, Depends(UOWDep(ClientUOW))]
