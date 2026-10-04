from logging import getLogger
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.dependencies.redis import RedisDep
from core.dependencies.s3 import S3Dep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.reward import (
    RewardCreate,
    RewardPatch,
    RewardPut,
    RewardPutData,
    RewardRead,
)
from event.dependency.reward import RewardUOWDep
from event.filter.reward import RewardFilter
from event.service.reward import RewardService

router = APIRouter(prefix="/rewards", tags=["reward"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_rewards(
    uow: RewardUOWDep,
    user: UserJWTDep,
    filter: RewardFilter = FilterDepends(RewardFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[RewardRead]:
    return PageV1[RewardRead].from_dto(
        await RewardService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_reward(
    user: SuperUserJWTDep,
    uow: RewardUOWDep,
    redis: RedisDep,
    s3: S3Dep,
    participation_id: Annotated[UUID, Form()],
    name: Annotated[str, Form(max_length=128)],
    degree: Annotated[int | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> RewardRead:
    result = await RewardService(uow, redis, s3).create(
        RewardCreate(
            file=file, participation_id=participation_id, name=name, degree=degree
        ).to_dto()
    )
    return RewardRead.from_dto(result)


@router.get(
    "/{reward_id}",
    responses={**auth_responses(), **entity_not_found_responses("reward")},
)
async def get_reward(
    reward_id: UUID,
    user: UserJWTDep,
    redis: RedisDep,
    s3: S3Dep,
    uow: RewardUOWDep,
) -> RewardRead:
    return RewardRead.from_dto(await RewardService(uow, redis, s3).read(reward_id))


@router.put(
    "/{reward_id}",
    responses={**auth_responses(), **entity_not_found_responses("reward")},
)
async def put_reward(
    reward_id: UUID,
    reward: RewardPutData,
    user: SuperUserJWTDep,
    redis: RedisDep,
    s3: S3Dep,
    uow: RewardUOWDep,
) -> RewardRead:
    result = await RewardService(uow, redis, s3).put(
        RewardPut(id=reward_id, **reward.model_dump()).to_dto()
    )
    return RewardRead.from_dto(result)


@router.patch(
    "/{reward_id}",
    responses={**auth_responses(), **entity_not_found_responses("reward")},
)
async def patch_reward(
    reward_id: UUID,
    user: SuperUserJWTDep,
    uow: RewardUOWDep,
    redis: RedisDep,
    s3: S3Dep,
    name: Annotated[str | None, Form(max_length=128)] = None,
    degree: Annotated[int | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> RewardRead:
    given = {
        key: value
        for key, value in {"name": name, "degree": degree, "file": file}.items()
        if value is not None
    }
    result = await RewardService(uow, redis, s3).patch(
        RewardPatch.model_validate({"id": reward_id, **given}).to_dto()
    )
    return RewardRead.from_dto(result)


@router.delete(
    "/{reward_id}",
    responses={**auth_responses(), **entity_not_found_responses("reward")},
)
async def delete_reward(
    reward_id: UUID, user: SuperUserJWTDep, s3: S3Dep, uow: RewardUOWDep
) -> None:
    await RewardService(uow, s3=s3).delete(reward_id)
