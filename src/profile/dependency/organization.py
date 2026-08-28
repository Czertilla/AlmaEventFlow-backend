from profile.uow.organization import OrganizationUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
