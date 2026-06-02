from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.reward import RewardORM


class RewardFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    class Constants(Filter.Constants):
        model = RewardORM
        search_model_fields = ["name"]
