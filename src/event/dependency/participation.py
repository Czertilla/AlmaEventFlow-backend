from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.participation import ParticipationUOW


ParticipationUOWDep = Annotated[
    ParticipationUOW, Depends(UOWDep(ParticipationUOW))
]
