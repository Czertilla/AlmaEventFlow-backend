from logging import getLogger
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import UploadFile
from redis import Redis

from core.dependencies.redis import redis
from core.dto.base import dto_dict
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from core.utils.requirer import required_field
from core.utils.s3_client import S3Client
from event.dto.reward import (
    RewardCreateDTO,
    RewardDTO,
    RewardFilterDTO,
    RewardPatchDTO,
    RewardPutDTO,
)
from event.exc.event import RewardNotExistsException
from event.filter.reward import RewardFilter
from event.models.reward import RewardORM
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
    async def _put_file(self, file: UploadFile, file_id: UUID):
        await self.s3.put_file(
            (file_id := str(file_id)),
            await file.read(),
            ContentType=file.content_type,
            ContentDisposition='filename="' f'{quote(file.filename)}"',
        )

    @staticmethod
    async def _to_dto(
        reward: RewardORM, file_link: str | None = None
    ) -> RewardDTO:
        return RewardDTO(
            id=reward.id,
            participation_id=reward.participation_id,
            name=reward.name,
            degree=reward.degree,
            file_link=file_link,
        )

    async def _resolve_file_link(self, reward: RewardORM) -> str | None:
        if not reward.file_id:
            return None
        return await self._get_presigned_file(reward.file_id)

    @required_transaction
    async def _create(self, reward_create: RewardCreateDTO) -> RewardORM:
        reward_data = dto_dict(reward_create, exclude={"file"})
        if reward_create.file:
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
        reward = await self.uow.rewards.update_one(reward_id, reward_data, flush)
        if reward is None:
            raise RewardNotExistsException()
        return reward

    @required_transaction
    async def _delete(self, reward_id: UUID) -> None:
        await self.uow.rewards.delete_one(reward_id)

    async def create(self, reward_create: RewardCreateDTO) -> RewardDTO:
        async with self.uow as uow:
            reward = await self._create(reward_create)
            file_link = None
            if reward_create.file:
                await self._put_file(reward_create.file, reward.file_id)
                file_link = await self._get_presigned_file(reward.file_id)
            result = await self._to_dto(reward, file_link)
            await uow.commit()
        return result

    async def read(self, reward_id: UUID) -> RewardDTO:
        async with self.uow:
            reward = await self._read(reward_id)
            if reward is None:
                raise RewardNotExistsException()
            file_link = await self._resolve_file_link(reward)
        return await self._to_dto(reward, file_link)

    async def patch(self, reward_patch: RewardPatchDTO) -> RewardDTO:
        async with self.uow as uow:
            reward_data = dto_dict(reward_patch, only_set=True)
            reward = await self._update(reward_patch.id, reward_data)
            file_link = None
            if reward_patch.file:
                await self._put_file(reward_patch.file, reward.file_id)
                file_link = await self._get_presigned_file(reward.file_id)
            result = await self._to_dto(reward, file_link)
            await uow.commit()
        return result

    async def put(self, reward_put: RewardPutDTO) -> RewardDTO:
        async with self.uow as uow:
            reward_data = dto_dict(reward_put, exclude={"id"})
            reward = await self._update(reward_put.id, reward_data)
            file_link = await self._resolve_file_link(reward)
            result = await self._to_dto(reward, file_link)
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

    async def search(
        self, filter: RewardFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[RewardDTO]:
        async with self.uow as uow:
            orm_filter = RewardFilter.from_dto(filter)
            items, total = await uow.rewards.search(orm_filter, page_params)
            return PageDTO(
                items=[await self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
