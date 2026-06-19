from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.server_http import (
    HTTPServerConfig,
    TrustedForwardedHeadersMiddleware,
    create_http_app,
)


def test_http_bearer_token_protects_mcp_route() -> None:
    app = create_http_app(
        TossInvestRemoteServerConfig("client-id", "client-secret"),
        HTTPServerConfig(bearer_token="secret"),
    )

    with TestClient(app) as client:
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_http_bearer_token_does_not_protect_healthz() -> None:
    app = create_http_app(
        TossInvestRemoteServerConfig("client-id", "client-secret"),
        HTTPServerConfig(bearer_token="secret"),
    )

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200


def test_origin_validation_rejects_untrusted_origin() -> None:
    app = create_http_app(
        TossInvestRemoteServerConfig("client-id", "client-secret"),
        HTTPServerConfig(allowed_origins=("https://trusted.example",)),
    )

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden_origin"}


def test_forwarded_headers_apply_only_for_trusted_proxy() -> None:
    async def endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"scheme": request.url.scheme, "host": request.url.hostname})

    app = Starlette(routes=[Route("/", endpoint)])
    wrapped = TrustedForwardedHeadersMiddleware(app, trusted_proxies=("10.0.0.0/8",))

    with TestClient(wrapped) as client:
        response = client.get(
            "/",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "public.example",
            },
        )

    assert response.json() == {"scheme": "http", "host": "testserver"}


def test_forwarded_headers_apply_for_trusted_proxy() -> None:
    async def endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"scheme": request.url.scheme, "host": request.url.hostname})

    app = Starlette(routes=[Route("/", endpoint)])
    wrapped = TrustedForwardedHeadersMiddleware(app, trusted_proxies=("10.0.0.0/8",))

    with TestClient(wrapped, client=("10.1.2.3", 50000)) as client:
        response = client.get(
            "/",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "public.example",
            },
        )

    assert response.json() == {"scheme": "https", "host": "public.example"}
