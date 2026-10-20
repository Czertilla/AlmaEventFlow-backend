from collections.abc import Sequence
from typing import Any

from beanie import (
    Document,
    init_beanie,  # pyright: ignore[reportUnknownVariableType]  # beanie leaves AsyncDatabase unparameterized
)
from pymongo import AsyncMongoClient

from core.config.settings import settings

_client: AsyncMongoClient[dict[str, Any]] | None = None


def get_client(host: str = settings.MONGO_URL) -> AsyncMongoClient[dict[str, Any]]:
    global _client
    if _client is None:
        _client = AsyncMongoClient(host)
    return _client


async def init(
    document_models: Sequence[type[Document]] | None = None,
    host: str = settings.MONGO_URL,
    db_name: str = settings.DB_NAME,
) -> None:
    if document_models is None:
        document_models = []
    client = get_client(host)

    await init_beanie(database=client[db_name], document_models=document_models)
