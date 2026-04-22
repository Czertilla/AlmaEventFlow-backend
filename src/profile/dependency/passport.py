from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.passport import PassportUOW


PassportUOWDep = Annotated[PassportUOW, Depends(UOWDep(PassportUOW))]
