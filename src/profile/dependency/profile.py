from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.profile import (
    ProfilePassportUOW,
    ProfileUOW,
    ProfileExtendedUOW,
)


ProfileUOWDep = Annotated[ProfileUOW, Depends(UOWDep(ProfileUOW))]
ProfilePassportUOWDep = Annotated[
    ProfilePassportUOW, Depends(UOWDep(ProfilePassportUOW))
]
ProfileExtendedUOWDep = Annotated[
    ProfileExtendedUOW, Depends(UOWDep(ProfileExtendedUOW))
]
