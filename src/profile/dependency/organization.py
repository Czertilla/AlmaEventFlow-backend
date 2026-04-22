from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.organization import OrganizationUOW


OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
