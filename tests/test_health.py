from __future__ import annotations

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.server_http import HTTPServerConfig, create_http_app

from .conftest import lifespan_asgi_client


async def test_healthz_returns_healthy_response_without_tossinvest_api_calls() -> None:
    app = create_http_app(
        TossInvestRemoteServerConfig("client-id", "client-secret"),
        HTTPServerConfig(),
    )

    async with lifespan_asgi_client(app) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
