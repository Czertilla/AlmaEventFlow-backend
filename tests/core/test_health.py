import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from core.api.v1.health import health_router
from core.utils.healthcheck import check


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/up" else 503)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return None


@pytest.fixture
def server() -> Iterator[int]:
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_port
    finally:
        httpd.shutdown()
        httpd.server_close()


async def test_the_health_router_reports_the_service_and_the_app_version() -> None:
    app = FastAPI(version="1.2.3")
    app.include_router(health_router("demo"), prefix="/demo/v1")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        response = await client.get("/demo/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "demo", "version": "1.2.3"}


def test_the_probe_passes_only_on_a_200(server: int) -> None:
    assert check("/up", server)
    assert not check("/down", server)


def test_the_probe_fails_when_nothing_listens() -> None:
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]

    assert not check("/up", port)
