from profile.uow.profile import (
    ProfileExtendedUOW,
    ProfilePassportUOW,
    ProfileUOW,
)
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

ProfileUOWDep = Annotated[ProfileUOW, Depends(UOWDep(ProfileUOW))]
ProfilePassportUOWDep = Annotated[
    ProfilePassportUOW, Depends(UOWDep(ProfilePassportUOW))
]
ProfileExtendedUOWDep = Annotated[
    ProfileExtendedUOW, Depends(UOWDep(ProfileExtendedUOW))
]
