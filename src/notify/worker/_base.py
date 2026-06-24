import asyncio
from abc import ABC, abstractmethod
from contextlib import suppress
from logging import getLogger

logger = getLogger(__name__)


class PollingWorker(ABC):
    """Background loop running ``work`` repeatedly. It sleeps for ``idle_seconds``
    only when a tick reports no work, so a backlog is drained promptly while an
    idle worker stays cheap."""

    def __init__(self, name: str, idle_seconds: float) -> None:
        self._name = name
        self._idle = idle_seconds
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=self._name)
        logger.info("%s started", self._name)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("%s stopped", self._name)

    async def _run(self) -> None:
        while not self._stop.is_set():
            if await self._safe_work() == 0:
                await asyncio.sleep(self._idle)

    async def _safe_work(self) -> int:
        try:
            return await self.work()
        except Exception:
            logger.exception("%s tick failed", self._name)
            await asyncio.sleep(self._idle)
            return 0

    @abstractmethod
    async def work(self) -> int:
        """Performs one unit of work; returns how many items were processed."""
        raise NotImplementedError
