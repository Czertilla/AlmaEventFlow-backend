from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from profile.uow.person import PersonContactUOW, PersonUOW


PersonUOWDep = Annotated[PersonUOW, Depends(UOWDep(PersonUOW))]
PersonContactUOWDep = Annotated[
    PersonContactUOW, Depends(UOWDep(PersonContactUOW))
]
