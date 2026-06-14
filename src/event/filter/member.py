from uuid import UUID
from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.member import MemberORM


class MemberFilter(Filter):
    order_by: list[str] | None = ["person__surname", "person__name", "person__patronymic"]
    is_active: bool = True
    collective_id: UUID | None = None
    person_id: UUID | None = None

    class Constants(Filter.Constants):
        model = MemberORM

    def sort(self, query):
        if not self.ordering_values:
            return query

        joined_rels = set()

        for field_name in self.ordering_values:
            direction = Filter.Direction.asc
            if field_name.startswith("-"):
                direction = Filter.Direction.desc
            field_name = field_name.replace("-", "").replace("+", "")

            if "__" in field_name:
                parts = field_name.split("__")
                model = self.Constants.model
                for part in parts[:-1]:
                    rel = getattr(model, part)
                    if rel not in joined_rels:
                        query = query.join(rel)
                        joined_rels.add(rel)
                    model = rel.property.mapper.class_
                order_by_field = getattr(model, parts[-1])
            else:
                order_by_field = getattr(self.Constants.model, field_name)

            query = query.order_by(getattr(order_by_field, direction)())

        return query
