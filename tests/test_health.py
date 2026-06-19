from __future__ import annotations

from starlette.testclient import TestClient

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.server_http import HTTPServerConfig, create_http_app


def test_healthz_returns_healthy_response_without_tossinvest_api_calls() -> None:
    app = create_http_app(
        TossInvestRemoteServerConfig("client-id", "client-secret"),
        HTTPServerConfig(),
    )

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
