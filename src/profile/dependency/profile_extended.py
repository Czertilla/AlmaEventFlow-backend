from profile.uow.profile_extended import ProfileExtendedUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

ProfileExtendedUOWDep = Annotated[
    ProfileExtendedUOW, Depends(UOWDep(ProfileExtendedUOW))
]
