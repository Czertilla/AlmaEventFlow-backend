from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.me import EventComposeUOW, ParticipationComposeUOW


EventComposeUOWDep = Annotated[EventComposeUOW, Depends(UOWDep(EventComposeUOW))]
ParticipationComposeUOWDep = Annotated[ParticipationComposeUOW, Depends(UOWDep(ParticipationComposeUOW))]
