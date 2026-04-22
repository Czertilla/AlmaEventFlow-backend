from logging import getLogger
from urllib.parse import quote
from uuid import UUID, uuid4
from fastapi import UploadFile
from redis import Redis

from core.utils.requirer import required_field
from core.dependencies.redis import redis
from core.service.base import BaseService, required_transaction
from core.utils.s3_client import S3Client
from event.models.reward import RewardORM
from event.schema.reward import (
    RewardCreate,
    RewardPatch,
    RewardPut,
    RewardRead,
)
from event.uow.reward import RewardUOW

logger = getLogger(__name__)


class RewardService(BaseService[RewardUOW]):
    required_redis = required_field("redis")
    required_s3 = required_field("s3")

    def __init__(self, uow, redis: Redis = None, s3: S3Client = None):
        super().__init__(uow)
        self.redis = redis
        self.s3 = s3

    @required_redis
    @required_s3
    async def _get_presigned_file(
        self, file_id: UUID, cached: bool = True
    ) -> str:
        if cached and (url := await redis.get(f"event:file_url:{file_id}")):
            return url
        expired = 3600
        await redis.setex(
            f"event:file_url:{file_id}",
            expired - 100,
            url := await self.s3.get_presigned_url(file_id, expired),
        )
        return url

    @required_s3
    async def _put_file(self, reward_create: RewardCreate, file_id: UUID):
        await self.s3.put_file(
            (file_id := str(file_id)),
            await reward_create.file.read(),
            ContentType=reward_create.file.content_type,
            ContentDisposition='filename="'
            f'{quote(reward_create.file.filename)}"',
        )

    @required_transaction
    async def _create(self, reward_create: RewardCreate) -> RewardORM:
        reward_data = reward_create.model_dump()
        upload_file: UploadFile = reward_data.pop("file", None)
        if upload_file:
            reward_data["file_id"] = uuid4()
        return await self.uow.rewards.add_n_return(data=reward_data)

    @required_transaction
    async def _read(self, reward_id: UUID) -> RewardORM | None:
        return await self.uow.rewards.get_by_id(reward_id)

    @required_transaction
    async def _update(
        self, reward_id: UUID, reward_data: dict, *, flush: bool = False
    ) -> RewardORM:
        reward_data.pop("file", None)
        return await self.uow.rewards.update_one(reward_id, reward_data, flush)

    @required_transaction
    async def _delete(self, reward_id: UUID) -> None:
        await self.uow.rewards.delete_one(reward_id)

    async def create(self, reward_create: RewardCreate) -> RewardRead:
        async with self.uow as uow:
            reward = await self._create(reward_create)
            result = RewardRead.model_validate(reward)
            if reward_create.file:
                await self._put_file(reward_create, reward.file_id)
                result.file_link = await self._get_presigned_file(
                    reward.file_id
                )
            await uow.commit()
        return result

    async def read(self, reward_id: UUID) -> RewardRead:
        async with self.uow:
            reward = await self._read(reward_id)
            result = RewardRead.model_validate(reward)
            result.file_link = await self._get_presigned_file(
                str(reward.file_id)
            )
        return result

    async def patch(self, reward_patch: RewardPatch) -> RewardRead:
        async with self.uow as uow:
            reward_data = reward_patch.model_dump(exclude_unset=True)
            reward = await self._update(reward_patch.id, reward_data)
            result = RewardRead.model_validate(reward)
            if reward_patch.file:
                await self._put_file(reward_patch, reward.file_id)
                result.file_link = await self._get_presigned_file(
                    str(reward.file_id)
                )
            await uow.commit()
        return result

    async def put(self, reward_put: RewardPut) -> RewardRead:
        async with self.uow as uow:
            reward_data = reward_put.model_dump()
            reward_id = reward_data.pop("id")
            reward = await self._update(reward_id, reward_data)
            result = RewardRead.model_validate(reward)
            if reward.file_id:
                result.file_link = await self._get_presigned_file(
                    str(reward.file_id)
                )
            await uow.commit()
        return result

    @required_s3
    async def delete(self, reward_id: UUID) -> None:
        async with self.uow as uow:
            file_id = (await self._read(reward_id)).file_id
            await self._delete(reward_id)
            if file_id:
                await self.s3.delete_file(str(file_id))
            await uow.commit()
