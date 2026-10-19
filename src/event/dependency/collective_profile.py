from typing import Annotated

from fastapi import Depends

from event.uow.collective_profile import CollectiveProfileUOW

from ._uow import UOWDep

CollectiveProfileUOWDep = Annotated[
    CollectiveProfileUOW, Depends(UOWDep(CollectiveProfileUOW))
]
