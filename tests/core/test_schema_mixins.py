from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.schema.v1.mixin.model import (
    IDMixinV1,
    PatchModelV1,
    PutUUIDMixinV1,
    TimestampMixinV1,
    UUIDMixinV1,
)


class Patch(PatchModelV1):
    name: str | None = None
    note: str | None = None


def test_patch_model_dump_keeps_only_fields_the_client_sent():
    assert Patch(name="a").model_dump() == {"name": "a"}


def test_patch_model_dump_keeps_an_explicit_null():
    assert Patch(note=None).model_dump() == {"note": None}


def test_put_uuid_mixin_generates_distinct_ids():
    class Put(BaseModel, PutUUIDMixinV1):
        name: str

    first, second = Put(name="a"), Put(name="a")

    assert isinstance(first.id, UUID)
    assert first.id != second.id


def test_identity_and_timestamp_mixins_declare_required_fields():
    class Read(BaseModel, UUIDMixinV1, TimestampMixinV1):
        pass

    class Numbered(BaseModel, IDMixinV1):
        pass

    assert set(Read.model_fields) == {"id", "created_at", "edited_at"}
    assert Read.model_fields["id"].annotation is UUID
    assert Read.model_fields["created_at"].annotation is datetime
    assert set(Numbered.model_fields) == {"id"}
