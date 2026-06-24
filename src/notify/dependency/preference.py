from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from notify.uow.preference import PreferenceUOW


PreferenceUOWDep = Annotated[PreferenceUOW, Depends(UOWDep(PreferenceUOW))]
