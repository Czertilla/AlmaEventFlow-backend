from profile.uow.access_log import AccessLogUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

AccessLogUOWDep = Annotated[AccessLogUOW, Depends(UOWDep(AccessLogUOW))]
