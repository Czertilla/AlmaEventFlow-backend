from core.uow.sqlalchemy import UnitOfWork
from event.repository.reward import RewardRepo


class RewardMixin:
    rewards: RewardRepo


class RewardUOW(UnitOfWork, RewardMixin): ...