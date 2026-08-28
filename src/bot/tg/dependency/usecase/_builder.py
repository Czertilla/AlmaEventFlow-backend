from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar

from aiogram.types import Message
from aiogram3_di import Depends

from bot.tg.dependency.text import TextBuilderDep

UseCaseT = TypeVar("UseCaseT")


def _validate_dependencies(
    usecase_cls: type[Any],
    dependencies: dict[str, Any],
) -> None:
    init_sig = inspect.signature(usecase_cls.__init__)
    init_params = set(init_sig.parameters.keys()) - {"self"}

    unknown = set(dependencies.keys()) - init_params
    if unknown:
        raise TypeError(
            f"{usecase_cls.__name__}: unknown constructor args: {sorted(unknown)}"
        )


def _parameter(name: str, dep_type: type[Any]):
    if dep_type == Message and name == "message":
        name = "event"
    return inspect.Parameter(
        name=name,
        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=dep_type,
    )

def _apply_aliases(arguments: dict[str, Any]):
    if "event" in arguments:
        message = arguments.pop("event")
        if isinstance(message, Message) and "message" not in arguments:
            arguments["message"] = message

def _build_provider_function(
    usecase_cls: type[UseCaseT],
    dependencies: dict[str, Any],
) -> Callable[..., UseCaseT]:
    params = []
    annotations: dict[str, Any] = {}

    for name, dep_type in dependencies.items():
        parameter = _parameter(name, dep_type)
        params.append(parameter)
        annotations[parameter.name] = parameter.annotation

    signature = inspect.Signature(parameters=params)

    def provider(*args, **kwargs) -> UseCaseT:
        bound = signature.bind(*args, **kwargs)
        _apply_aliases(arguments := bound.arguments)
        return usecase_cls(**arguments)

    provider.__name__ = f"provide_{usecase_cls.__name__.lower()}"
    provider.__signature__ = signature
    provider.__annotations__ = annotations | {"return": usecase_cls}

    return provider


def build_usecase_dep(
    usecase_cls: type[UseCaseT],
    /,
    **dependencies: Any,
):
    _validate_dependencies(usecase_cls, dependencies)
    provider = _build_provider_function(usecase_cls, dependencies)
    return Depends(provider)


class UseCaseDepBuilder:
    def __init__(self, **default_dependencies: Any):
        self._defaults = dict(default_dependencies)

    def with_defaults(self, **extra_defaults: Any) -> "UseCaseDepBuilder":
        merged = {**self._defaults, **extra_defaults}
        return UseCaseDepBuilder(**merged)

    def __call__(
        self,
        usecase_cls: type[UseCaseT],
        /,
        **dependencies: Any,
    ):
        merged = {**self._defaults, **dependencies}
        return build_usecase_dep(usecase_cls, **merged)


usecase_dep = UseCaseDepBuilder(
    text_builder=TextBuilderDep,
)
