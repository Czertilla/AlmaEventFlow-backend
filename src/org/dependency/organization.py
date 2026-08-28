from typing import Annotated

from fastapi import Depends

from org.uow.organization import OrganizationUOW

from ._uow import UOWDep

OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
