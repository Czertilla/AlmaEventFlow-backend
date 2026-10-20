from collections.abc import Callable, Mapping
from functools import wraps
from logging import Logger
from types import TracebackType
from typing import cast
from uuid import uuid4

type ExcInfo = (
    bool
    | BaseException
    | tuple[type[BaseException], BaseException, TracebackType | None]
    | tuple[None, None, None]
    | None
)


def inject_err_id[**P](func: Callable[P, None]) -> Callable[P, None]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
        extra = cast("dict[str, object]", kwargs.get("extra") or {})
        if "err_id" not in extra:
            extra.update({"err_id": uuid4()})
        kwargs["extra"] = extra
        func(*args, **kwargs)
        return extra["err_id"]

    # Logger.error and friends return None; the generated id is returned on top
    return cast("Callable[P, None]", wrapper)


class IDLogger(Logger):
    @inject_err_id
    def error(
        self,
        msg: object,
        *args: object,
        exc_info: ExcInfo = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().error(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @inject_err_id
    def exception(
        self,
        msg: object,
        *args: object,
        exc_info: ExcInfo = True,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().exception(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @inject_err_id
    def critical(
        self,
        msg: object,
        *args: object,
        exc_info: ExcInfo = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().critical(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )