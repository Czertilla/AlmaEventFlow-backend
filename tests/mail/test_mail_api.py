import httpx


async def test_the_mail_app_answers_its_health_probe() -> None:
    from mail.app.app import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        response = await client.get("/mail/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["service"]) == ("ok", "mail")
    assert body["version"] == app.version
