import inspect
from typing import Any

from fastapi import Query
from fastapi_filter import FilterDepends as _FilterDepends
from fastapi_filter.base.filter import BaseFilterModel


def FilterDepends(  # noqa: N802
    filter_cls: type[BaseFilterModel], **kwargs: Any
) -> Any:
    """``FilterDepends`` that keeps field descriptions in the OpenAPI schema."""
    dependency = _FilterDepends(filter_cls, **kwargs)
    wrapper: Any = dependency.dependency
    parameters: list[inspect.Parameter] = []
    for parameter in inspect.signature(wrapper).parameters.values():
        field = filter_cls.model_fields.get(parameter.name)
        if field is not None and field.description:
            empty = parameter.default is inspect.Parameter.empty
            default = ... if empty else parameter.default
            parameter = parameter.replace(
                default=Query(default, description=field.description)
            )
        parameters.append(parameter)
    wrapper.__signature__ = inspect.Signature(parameters)
    return dependency
