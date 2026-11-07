from math import ceil
from profile.exc.access_request import TooManyRequests
from profile.uow.access_request import AccessRequestUOW
from profile.utils.rate_limit import RateLimiter
from typing import Annotated

from fastapi import Depends

from core.config.settings import settings
from core.dependencies.auth import UserJWTDep

from ._uow import UOWDep

AccessRequestUOWDep = Annotated[AccessRequestUOW, Depends(UOWDep(AccessRequestUOW))]

REQUEST_LIMIT = RateLimiter(lambda: settings.ACCESS_REQUESTS_PER_HOUR)
EXPORT_LIMIT = RateLimiter(lambda: settings.ACCESS_EXPORTS_PER_HOUR)


def _limited(limiter: RateLimiter):
    async def check(user: UserJWTDep) -> None:
        wait = limiter.allow(user.id)
        if wait is not None:
            raise TooManyRequests(headers={"Retry-After": str(max(ceil(wait), 1))})

    return check


RequestLimitDep = Annotated[None, Depends(_limited(REQUEST_LIMIT))]
ExportLimitDep = Annotated[None, Depends(_limited(EXPORT_LIMIT))]
