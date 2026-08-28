from typing import Annotated

from fastapi import Depends

from event.uow.member import MemberUOW

from ._uow import UOWDep

MemberUOWDep = Annotated[MemberUOW, Depends(UOWDep(MemberUOW))]
