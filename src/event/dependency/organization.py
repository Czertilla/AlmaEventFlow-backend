from typing import Annotated

from fastapi import Depends

from event.uow.organization import OrganizationUOW

from ._uow import UOWDep

OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
