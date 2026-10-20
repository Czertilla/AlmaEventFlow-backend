from profile.uow.reference import ReferenceUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

ReferenceUOWDep = Annotated[ReferenceUOW, Depends(UOWDep(ReferenceUOW))]
