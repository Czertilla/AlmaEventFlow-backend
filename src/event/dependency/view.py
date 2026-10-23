from typing import Annotated

from fastapi import Depends

from event.uow.view import ViewUOW

from ._uow import UOWDep

ViewUOWDep = Annotated[ViewUOW, Depends(UOWDep(ViewUOW))]
