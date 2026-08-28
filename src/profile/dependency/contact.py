from profile.uow.contact import ContactUOW
from profile.uow.person import PersonContactUOW
from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep

ContactUOWDep = Annotated[ContactUOW, Depends(UOWDep(ContactUOW))]
PersonContactUOWDep = Annotated[
    PersonContactUOW, Depends(UOWDep(PersonContactUOW))
]
