from copy import copy
from enum import Enum

import sqlalchemy.types as types


class ValuesEnum(types.TypeDecorator):
    impl = types.Enum

    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        objects = copy(self._object_lookup)
        objects.pop(None)
        self._reversed_object_lookup = {v.value: v for v in objects.values()}
        self._reversed_object_lookup[None] = None

    def process_bind_param(self, value, dialect):
        if isinstance(value, Enum):
            return value.value
        return value

    def _object_value_for_elem(self, value):
        return self._reversed_object_lookup[value]

    def result_processor(self, dialect, coltype):
        def process(value):
            value = self._object_value_for_elem(value)
            return value

        return process