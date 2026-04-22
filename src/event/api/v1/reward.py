from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.dependencies.redis import RedisDep
from core.dependencies.s3 import S3Dep
from event.dependency.reward import RewardUOWDep
from event.schema.reward import (
    RewardCreate,
    RewardCreateData,
    RewardPatch,
    RewardPatchData,
    RewardPut,
    RewardPutData,
    RewardRead,
)
from event.service.reward import RewardService

router = APIRouter(prefix="/rewards", tags=["reward"])

logger = getLogger(__name__)


@router.post("")
async def create_reward(
    user: SuperUserJWTDep,
    participation_id: UUID,
    uow: RewardUOWDep,
    redis: RedisDep,
    s3: S3Dep,
    file: UploadFile,
    reward: RewardCreateData = Depends(),
) -> RewardRead:
    return await RewardService(uow, redis, s3).create(
        RewardCreate(
            file=file, participation_id=participation_id, **reward.model_dump()
        )
    )


@router.get("/{reward_id}")
async def get_reward(
    reward_id: UUID,
    user: UserJWTDep,
    redis: RedisDep,
    s3: S3Dep,
    uow: RewardUOWDep,
) -> RewardRead:
    return await RewardService(uow, redis, s3).read(reward_id)


@router.put("/{reward_id}")
async def put_reward(
    reward_id: UUID,
    reward: RewardPutData,
    user: SuperUserJWTDep,
    redis: RedisDep,
    s3: S3Dep,
    uow: RewardUOWDep,
) -> RewardRead:
    return await RewardService(uow, redis, s3).put(
        RewardPut(id=reward_id, **reward.model_dump())
    )


@router.patch("/{reward_id}")
async def patch_reward(
    reward_id: UUID,
    user: SuperUserJWTDep,
    uow: RewardUOWDep,
    file: UploadFile,
    redis: RedisDep,
    s3: S3Dep,
    reward: RewardPatchData = Depends(),
) -> RewardRead:
    return await RewardService(uow, redis, s3).patch(
        RewardPatch(id=reward_id, **reward.model_dump())
    )


@router.delete("/{reward_id}")
async def delete_reward(
    reward_id: UUID, user: SuperUserJWTDep, s3: S3Dep, uow: RewardUOWDep
) -> None:
    await RewardService(uow, s3=s3).delete(reward_id)
