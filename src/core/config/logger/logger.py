from functools import wraps
from logging import Logger
from typing import Callable
from uuid import uuid4


def inject_err_id(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        extra = kwargs.get("extra", None) or {}
        if "err_id" not in extra:
            extra.update({"err_id": uuid4()})
        kwargs["extra"] = extra
        func(*args, **kwargs)
        return extra["err_id"]

    return wrapper


class IDLogger(Logger):
    @inject_err_id
    def error(
        self,
        msg,
        *args,
        exc_info=None,
        stack_info=False,
        stacklevel=1,
        extra=None,
    ):
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
        msg,
        *args,
        exc_info=True,
        stack_info=False,
        stacklevel=1,
        extra=None,
    ):
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
        msg,
        *args,
        exc_info=None,
        stack_info=False,
        stacklevel=1,
        extra=None,
    ):
        return super().critical(
            msg,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )