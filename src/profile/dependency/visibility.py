from profile.uow.visibility import VisibilityUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

VisibilityUOWDep = Annotated[VisibilityUOW, Depends(UOWDep(VisibilityUOW))]
