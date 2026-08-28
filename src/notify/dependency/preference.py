from typing import Annotated

from fastapi import Depends

from notify.uow.preference import PreferenceUOW

from ._uow import UOWDep

PreferenceUOWDep = Annotated[PreferenceUOW, Depends(UOWDep(PreferenceUOW))]
