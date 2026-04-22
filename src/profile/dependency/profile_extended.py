from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.profile_extended import ProfileExtendedUOW


ProfileExtendedUOWDep = Annotated[
    ProfileExtendedUOW, Depends(UOWDep(ProfileExtendedUOW))
]
