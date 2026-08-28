from typing import Annotated

from fastapi import Depends

from notify.uow.client import ClientUOW

from ._uow import UOWDep

ClientUOWDep = Annotated[ClientUOW, Depends(UOWDep(ClientUOW))]
