from profile.uow.person_key import PersonalDataUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

PersonalDataUOWDep = Annotated[PersonalDataUOW, Depends(UOWDep(PersonalDataUOW))]
