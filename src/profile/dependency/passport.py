from profile.uow.passport import PassportUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

PassportUOWDep = Annotated[PassportUOW, Depends(UOWDep(PassportUOW))]
