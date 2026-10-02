from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Concatenate, TypeVar

from core.utils.abstract.unit_of_work import ABCUnitOfWork

T = TypeVar("T", bound=ABCUnitOfWork)


class BaseService[T: ABCUnitOfWork]:
    """
    Base service class for application services.

    Provides a common interface for services that require a Unit of Work.

    Attributes:
        uow (ABCUnitOfWork): The Unit of Work instance used by the service.
    """

    def __init__(self, uow: T) -> None:
        """
        Initializes the BaseService with a Unit of Work.

        Args:
            uow (ABCUnitOfWork): The Unit of Work instance.
        """
        self.uow: T = uow


class RequiredTransactionException(Exception): ...


def required_transaction[S: BaseService[Any], **P, R](
    func: Callable[Concatenate[S, P], Awaitable[R]],
) -> Callable[Concatenate[S, P], Awaitable[R]]:
    @wraps(func)
    async def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
        if not self.uow.is_transacting():
            raise RequiredTransactionException
        return await func(self, *args, **kwargs)

    return wrapper


def autocommit[S: BaseService[Any], **P, R](
    func: Callable[Concatenate[S, P], Awaitable[R]],
) -> Callable[Concatenate[S, P], Awaitable[R]]:
    @wraps(func)
    async def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
        result = await func(self, *args, **kwargs)
        await self.uow.commit()
        return result

    return wrapper
