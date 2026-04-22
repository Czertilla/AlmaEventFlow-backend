from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.organization import OrganizationUOW


OrganizationUOWDep = Annotated[
    OrganizationUOW, Depends(UOWDep(OrganizationUOW))
]
