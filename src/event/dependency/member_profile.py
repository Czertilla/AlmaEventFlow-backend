from typing import Annotated

from fastapi import Depends

from event.uow.member_profile import MemberProfileUOW

from ._uow import UOWDep

MemberProfileUOWDep = Annotated[
    MemberProfileUOW, Depends(UOWDep(MemberProfileUOW))
]
