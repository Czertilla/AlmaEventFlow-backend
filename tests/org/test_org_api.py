import httpx
from support.http import principal

BASE = "/org/v1"
ADMIN = principal(superuser=True)
USER = principal()


async def test_a_university_reads_back_with_timestamps_and_changes_by_patch(
    api: httpx.AsyncClient,
) -> None:
    created = await api.post(
        f"{BASE}/universities", json={"name": "MSU", "acronym": "M"}, headers=ADMIN
    )
    university_id = created.json()["id"]

    read = await api.get(f"{BASE}/universities/{university_id}", headers=USER)
    patched = await api.patch(
        f"{BASE}/universities/{university_id}", json={"name": "MSU-2"}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/universities/{university_id}", json={"name": "SPbU"}, headers=ADMIN
    )

    assert created.status_code == 200, created.text
    assert read.json()["created_at"]
    assert read.json()["edited_at"] is None
    assert (patched.json()["name"], patched.json()["acronym"]) == ("MSU-2", "M")
    assert patched.json()["edited_at"] is not None
    assert (replaced.json()["name"], replaced.json()["acronym"]) == ("SPbU", None)


async def test_writes_are_for_superusers(api: httpx.AsyncClient) -> None:
    response = await api.post(
        f"{BASE}/universities", json={"name": "MSU"}, headers=USER
    )

    assert response.status_code == 403


async def test_the_path_id_decides_which_organization_is_patched(
    api: httpx.AsyncClient,
) -> None:
    first = await api.post(f"{BASE}/organizations", json={"name": "A"}, headers=ADMIN)
    second = await api.post(f"{BASE}/organizations", json={"name": "B"}, headers=ADMIN)

    patched = await api.patch(
        f"{BASE}/organizations/{first.json()['id']}",
        json={"id": second.json()["id"], "name": "A2"},
        headers=ADMIN,
    )
    other = await api.get(f"{BASE}/organizations/{second.json()['id']}", headers=USER)

    assert first.json()["type"] == "organization"
    assert patched.json()["id"] == first.json()["id"]
    assert patched.json()["name"] == "A2"
    assert other.json()["name"] == "B"


async def test_an_organization_cannot_be_created_with_another_type_or_replaced(
    api: httpx.AsyncClient,
) -> None:
    created = await api.post(
        f"{BASE}/organizations",
        json={"name": "Fake", "type": "university"},
        headers=ADMIN,
    )
    replaced = await api.put(
        f"{BASE}/organizations/{created.json()['id']}",
        json={"name": "X"},
        headers=ADMIN,
    )

    assert created.json()["type"] == "organization"
    assert replaced.status_code == 405


async def test_organizations_are_filtered_by_type_and_sorted(
    api: httpx.AsyncClient,
) -> None:
    await api.post(f"{BASE}/organizations", json={"name": "Plain"}, headers=ADMIN)
    await api.post(f"{BASE}/universities", json={"name": "Uni"}, headers=ADMIN)
    await api.post(f"{BASE}/collectives", json={"name": "Club"}, headers=ADMIN)

    only_universities = await api.get(
        f"{BASE}/organizations", params={"type": "university"}, headers=USER
    )
    several = await api.get(
        f"{BASE}/organizations",
        params={"type__in": "university,collective", "order_by": "-name"},
        headers=USER,
    )
    newest = await api.get(
        f"{BASE}/organizations", params={"order_by": "-created_at"}, headers=USER
    )
    bad_type = await api.get(
        f"{BASE}/organizations", params={"type": "castle"}, headers=USER
    )
    bad_order = await api.get(
        f"{BASE}/organizations", params={"order_by": "principal"}, headers=USER
    )

    assert [o["name"] for o in only_universities.json()["items"]] == ["Uni"]
    assert [o["name"] for o in several.json()["items"]] == ["Uni", "Club"]
    assert newest.json()["items"][0]["name"] == "Club"
    assert bad_type.status_code == 422
    assert bad_order.status_code == 422


async def test_faculties_are_filtered_by_university(api: httpx.AsyncClient) -> None:
    university = await api.post(
        f"{BASE}/universities", json={"name": "MSU"}, headers=ADMIN
    )
    uni_id = university.json()["id"]
    await api.post(
        f"{BASE}/faculties",
        json={"name": "Math", "university_id": uni_id},
        headers=ADMIN,
    )
    await api.post(f"{BASE}/faculties", json={"name": "Free"}, headers=ADMIN)

    mine = await api.get(
        f"{BASE}/faculties", params={"university_id": uni_id}, headers=USER
    )
    unattached = await api.get(
        f"{BASE}/faculties", params={"university_id__isnull": True}, headers=USER
    )

    assert [f["name"] for f in mine.json()["items"]] == ["Math"]
    assert mine.json()["items"][0]["created_at"]
    assert [f["name"] for f in unattached.json()["items"]] == ["Free"]


async def test_timestamp_filters_accept_plain_dates(api: httpx.AsyncClient) -> None:
    await api.post(f"{BASE}/universities", json={"name": "MSU"}, headers=ADMIN)

    since = await api.get(
        f"{BASE}/universities", params={"created_at__gte": "2020-01-01"}, headers=USER
    )
    until = await api.get(
        f"{BASE}/universities", params={"created_at__lte": "2020-01-01"}, headers=USER
    )

    assert since.status_code == 200, since.text
    assert since.json()["pagination"]["total"] == 1
    assert until.status_code == 200, until.text
    assert until.json()["pagination"]["total"] == 0
