from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from org.uow.organization import OrganizationUOW


OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
