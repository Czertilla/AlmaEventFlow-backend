from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.schema.message.org import OrganizationData
from org.bootstrap.republish import announce


async def _organization(
    engine: AsyncEngine, kind: str, name: str, head: UUID | None
) -> UUID:
    organization_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type, principal_id, created_at) "
                "VALUES (:id, :name, :type, :head, now())"
            ),
            {"id": organization_id, "name": name, "type": kind, "head": head},
        )
    return organization_id


async def test_universities_and_faculties_are_announced_with_their_heads(
    org_engine: AsyncEngine, org_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    head = uuid4()
    async with org_engine.begin() as conn:
        await conn.execute(text("INSERT INTO person (id) VALUES (:id)"), {"id": head})
    university = await _organization(org_engine, "university", "State", head)
    faculty = await _organization(org_engine, "faculty", "Physics", None)
    await _organization(org_engine, "collective", "Choir", head)
    published: list[list[OrganizationData]] = []

    async def publish(organizations: list[OrganizationData]) -> None:
        published.append(organizations)

    count = await announce(org_sessionmaker, publish)

    assert count == 2
    announced = {item.id: item for item in published[0]}
    assert set(announced) == {university, faculty}
    assert announced[university].principal_id == head
    assert announced[faculty].principal_id is None


async def test_a_dry_run_announces_nothing(
    org_engine: AsyncEngine, org_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await _organization(org_engine, "university", "State", None)
    published: list[list[OrganizationData]] = []

    async def publish(organizations: list[OrganizationData]) -> None:
        published.append(organizations)

    count = await announce(org_sessionmaker, publish, dry_run=True)

    assert count == 1
    assert published == []
