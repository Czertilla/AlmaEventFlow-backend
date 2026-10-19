from profile.uow.my_profile import MyProfileUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

MyProfileUOWDep = Annotated[MyProfileUOW, Depends(UOWDep(MyProfileUOW))]
