from typing import Annotated

from fastapi import Depends

from org.uow.person import PersonUOW

from ._uow import UOWDep

PersonUOWDep = Annotated[PersonUOW, Depends(UOWDep(PersonUOW))]
