from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.member import MemberUOW


MemberUOWDep = Annotated[MemberUOW, Depends(UOWDep(MemberUOW))]
