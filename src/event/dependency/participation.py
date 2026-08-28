from typing import Annotated

from fastapi import Depends

from event.uow.participation import ParticipationUOW

from ._uow import UOWDep

ParticipationUOWDep = Annotated[
    ParticipationUOW, Depends(UOWDep(ParticipationUOW))
]
