from functools import wraps
from typing import Generic, TypeVar
from core.utils.abstract.unit_of_work import ABCUnitOfWork
from typing import Awaitable


T = TypeVar("T", bound=ABCUnitOfWork)


class BaseService(Generic[T]):
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


def required_transaction(func):
    if isinstance(func, Awaitable):

        @wraps(func)
        def wrapper(self: BaseService[T], *args, **kwargs):
            if not self.uow.is_transacting():
                raise RequiredTransactionException
            return func(self, *args, *kwargs)
    else:

        @wraps(func)
        async def wrapper(self: BaseService[T], *args, **kwargs):
            if not self.uow.is_transacting():
                raise RequiredTransactionException
            return await func(self, *args, *kwargs)

    return wrapper


def autocommit(func):
    @wraps(func)
    async def wrapper(self: BaseService[T], *args, **kwargs):
        result = await func(self, *args, **kwargs)
        await self.uow.commit()
        return result

    return wrapper
