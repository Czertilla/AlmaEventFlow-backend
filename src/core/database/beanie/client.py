from pymongo import AsyncMongoClient

from beanie import init_beanie, Document
from core.config.settings import settings

_client: AsyncMongoClient | None = None


def get_client(host: str = settings.MONGO_URL) -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = AsyncMongoClient(host)
    return _client


async def init(
    document_models: list[Document] = [],
    host: str = settings.MONGO_URL,
    db_name: str = settings.DB_NAME,
) -> None:
    client = get_client(host)

    await init_beanie(database=client[db_name], document_models=document_models)
