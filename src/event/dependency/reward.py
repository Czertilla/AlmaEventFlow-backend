from typing import Annotated

from fastapi import Depends

from event.uow.reward import RewardUOW

from ._uow import UOWDep

RewardUOWDep = Annotated[RewardUOW, Depends(UOWDep(RewardUOW))]
