from sqlalchemy.dialects.postgresql import insert

from core.repository.person import PersonBaseRepo

from org.models.person import PersonORM as Model


class PersonRepo(PersonBaseRepo[Model]):
    model = Model

    async def upsert(self, data, options=()):
        stmt = (
            insert(self.model)
            .values(**data)
            .on_conflict_do_nothing(
                index_elements=self.conflict_index_elements,
            )
            .options(*options)
            .returning(self.model)
        )
        return (await self.execute(stmt)).scalar_one_or_none()
