from __future__ import annotations

from tossinvest_mcp.config import TossInvestMCPServerConfig
from tossinvest_mcp.server_http import HTTPServerConfig, create_http_app

from .conftest import lifespan_asgi_client


async def test_healthz_returns_healthy_response_without_tossinvest_api_calls() -> None:
    app = create_http_app(
        TossInvestMCPServerConfig("client-id", "client-secret"),
        HTTPServerConfig(),
    )

    async with lifespan_asgi_client(app) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
