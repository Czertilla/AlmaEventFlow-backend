from typing import Annotated

from fastapi import Depends

from event.uow.me import EventComposeUOW, ParticipationComposeUOW

from ._uow import UOWDep

EventComposeUOWDep = Annotated[EventComposeUOW, Depends(UOWDep(EventComposeUOW))]
ParticipationComposeUOWDep = Annotated[ParticipationComposeUOW, Depends(UOWDep(ParticipationComposeUOW))]
