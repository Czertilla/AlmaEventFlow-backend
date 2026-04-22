from typing import Annotated

from fastapi import Depends

from ._uow import UOWDep
from event.uow.reward import RewardUOW


RewardUOWDep = Annotated[RewardUOW, Depends(UOWDep(RewardUOW))]
