"""
Debounce mechanism for state-based operations to prevent duplicate calls.
This implements an "inverted Lock" that delays execution and cancels
previous calls if new ones arrive for the same key.
"""
from asyncio import CancelledError, Lock, create_task, gather, sleep
from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram.fsm.context import FSMContext

logger = getLogger(__name__)

# Global debounce state storage
_debounce_tasks: Dict[str, Any] = {}
_debounce_locks: Dict[str, Lock] = {}


class DebounceManager:
    """Manager for debounced state operations."""

    def __init__(self, default_timeout: float = 0.5):
        """
        Initialize debounce manager.

        Args:
            default_timeout: Default timeout in seconds before executing
        """
        self.default_timeout = default_timeout

    async def debounce_call(
        self,
        state: FSMContext,
        func: Callable[..., Awaitable[Any]],
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Debounce a function call based on FSM state.

        Args:
            state: FSM context to use as key
            func: Function to debounce
            *args: Function arguments
            timeout: Optional timeout override
            **kwargs: Function keyword arguments

        Returns:
            Function result or None if cancelled
        """
        state_key = str(state.key)
        actual_timeout = timeout if timeout is not None else self.default_timeout

        # Get or create lock for this state
        if state_key not in _debounce_locks:
            _debounce_locks[state_key] = Lock()

        lock = _debounce_locks[state_key]

        async with lock:
            # Cancel previous task if exists
            if state_key in _debounce_tasks:
                previous_task = _debounce_tasks[state_key]
                if not previous_task.done():
                    logger.debug(f"Cancelling previous debounce task for state {state_key}")
                    previous_task.cancel()
                    try:
                        await previous_task
                    except CancelledError:
                        logger.debug(f"Previous task for state {state_key} was cancelled")

            # Create new task
            task = create_task(self._execute_with_delay(
                state_key, func, actual_timeout, *args, **kwargs
            ))
            _debounce_tasks[state_key] = task

            logger.debug(f"Created debounce task for state {state_key}, timeout: {actual_timeout}s")

            # Wait for task completion
            try:
                result = await task
                return result
            except CancelledError:
                logger.debug(f"Debounce task for state {state_key} was cancelled before execution")
                return None

    async def _execute_with_delay(
        self,
        state_key: str,
        func: Callable[..., Awaitable[Any]],
        delay: float,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function after delay.

        Args:
            state_key: State identifier
            func: Function to execute
            delay: Delay in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        # Wait for the delay
        await sleep(delay)

        # Execute the function
        logger.debug(f"Executing debounced function for state {state_key}")
        result = await func(*args, **kwargs)

        # Clean up task reference
        if state_key in _debounce_tasks and _debounce_tasks[state_key].done():
            del _debounce_tasks[state_key]

        return result

    async def flush_all(self) -> None:
        """Execute all pending debounce tasks immediately."""
        tasks = []
        for state_key, task in _debounce_tasks.items():
            if not task.done():
                # Cancel delay and execute immediately
                task.cancel()
                try:
                    await task
                except CancelledError:
                    logger.info(f"Cancelled pending debounce task for state {state_key}")
                    pass

                # Execute immediately
                logger.info(f"Flushing debounce task for state {state_key}")
                tasks.append(create_task(self._execute_immediately(state_key)))

        if tasks:
            await gather(*tasks, return_exceptions=True)

    async def _execute_immediately(self, state_key: str) -> None:
        """Remove task reference for immediate execution."""
        if state_key in _debounce_tasks:
            del _debounce_tasks[state_key]


# Global debounce manager instance
_default_debounce_manager = DebounceManager()


async def debounce_state_call(
    state: FSMContext,
    func: Callable[..., Awaitable[Any]],
    *args,
    timeout: Optional[float] = None,
    **kwargs
) -> Any:
    """
    Convenience function to debounce state-based calls.

    Args:
        state: FSM context to use as key
        func: Function to debounce
        *args: Function arguments
        timeout: Optional timeout override
        **kwargs: Function keyword arguments

    Returns:
        Function result or None if cancelled
    """
    return await _default_debounce_manager.debounce_call(
        state, func, *args, timeout=timeout, **kwargs
    )


def get_debounce_manager(timeout: Optional[float] = None) -> DebounceManager:
    """
    Get debounce manager instance.

    Args:
        timeout: Optional timeout for the manager

    Returns:
        DebounceManager instance
    """
    if timeout is None:
        return _default_debounce_manager
    else:
        return DebounceManager(timeout)
