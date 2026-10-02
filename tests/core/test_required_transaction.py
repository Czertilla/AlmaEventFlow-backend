from typing import Any

import pytest

from core.service.base import (
    BaseService,
    RequiredTransactionException,
    required_transaction,  # pyright: ignore[reportUnknownVariableType]
)


class FakeUoW:
    def __init__(self, transacting: bool) -> None:
        self.transacting = transacting

    def is_transacting(self) -> bool:
        return self.transacting


class Service(BaseService[Any]):
    @required_transaction
    async def compute(self, base: int, *, flush: bool = False) -> tuple[int, bool]:
        return base, flush


async def test_keyword_arguments_reach_the_wrapped_method():
    service = Service(FakeUoW(transacting=True))

    assert await service.compute(1, flush=True) == (1, True)


async def test_the_method_is_refused_outside_a_transaction():
    service = Service(FakeUoW(transacting=False))

    with pytest.raises(RequiredTransactionException):
        await service.compute(1)
