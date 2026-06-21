from __future__ import annotations

from contextlib import AbstractContextManager
from types import TracebackType
from typing import cast

import pytest
from mcp.server.auth.provider import AccessToken
from tossinvest import OrderCreateRequest, OrderResponse

import tossinvest_mcp_remote.server as server_module
from tossinvest_mcp_remote.client_factory import ClientContextFactory
from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.errors import TossInvestMCPRemoteConfigError
from tossinvest_mcp_remote.server import (
    SERVER_INSTRUCTIONS,
    _authorize_live_order,
    _require_oauth_scopes,
    create_server,
)
from tossinvest_mcp_remote.server_http import _merged_scopes


def _property_enum(schema: dict[str, object], property_name: str) -> list[str]:
    properties = cast(dict[str, object], schema["properties"])
    enum = _schema_enum(schema, cast(dict[str, object], properties[property_name]))
    if enum is None:
        msg = f"{property_name} does not expose an enum."
        raise AssertionError(msg)
    return enum


def _schema_enum(schema: dict[str, object], property_schema: dict[str, object]) -> list[str] | None:
    enum = property_schema.get("enum")
    if isinstance(enum, list):
        return cast(list[str], enum)
    ref = property_schema.get("$ref")
    if isinstance(ref, str):
        defs = cast(dict[str, object], schema["$defs"])
        return _schema_enum(schema, cast(dict[str, object], defs[ref.removeprefix("#/$defs/")]))
    for key in ("anyOf", "oneOf"):
        options = property_schema.get(key)
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict):
                    nested_enum = _schema_enum(schema, cast(dict[str, object], option))
                    if nested_enum is not None:
                        return nested_enum
    return None


class _ConfirmOrders:
    account: str | int | None = None
    created_request: OrderCreateRequest | None = None

    def create_order(
        self,
        request: OrderCreateRequest,
        *,
        account: str | int | None = None,
    ) -> OrderResponse:
        self.account = account
        self.created_request = request
        return OrderResponse.model_validate({"orderId": "order-1"})


class _ConfirmClient:
    def __init__(self) -> None:
        self.orders = _ConfirmOrders()


class _ConfirmClientContext(AbstractContextManager[_ConfirmClient]):
    def __init__(self, client: _ConfirmClient) -> None:
        self.client = client

    def __enter__(self) -> _ConfirmClient:
        return self.client

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


async def test_create_server_registers_read_only_tools_only() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))
    tool_names = {tool.name for tool in await server.list_tools()}

    assert "list_accounts" in tool_names
    assert "find_account_by_number" in tool_names
    assert "get_price" in tool_names
    assert "get_buying_power" in tool_names
    assert {"create_order", "modify_order", "cancel_order"}.isdisjoint(tool_names)


async def test_account_scoped_tool_schema_uses_account_seq() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))
    tools = {tool.name: tool for tool in await server.list_tools()}
    schema = tools["get_buying_power"].inputSchema

    assert "account_seq" in schema["properties"]
    assert "account" not in schema["properties"]
    assert "accountSeq" in schema["properties"]["account_seq"]["description"]
    assert "accountNo" in schema["properties"]["account_seq"]["description"]


async def test_read_only_tool_schemas_expose_sdk_enums() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))
    tools = {tool.name: tool for tool in await server.list_tools()}

    list_orders_schema = tools["list_orders"].inputSchema
    assert list_orders_schema["properties"]["status"]["default"] == "OPEN"
    assert "status" not in list_orders_schema.get("required", [])
    assert _property_enum(list_orders_schema, "status") == ["OPEN", "CLOSED"]
    assert _property_enum(tools["get_candles"].inputSchema, "interval") == ["1m", "1d"]
    assert _property_enum(tools["get_exchange_rate"].inputSchema, "base_currency") == [
        "KRW",
        "USD",
    ]
    assert _property_enum(tools["get_exchange_rate"].inputSchema, "quote_currency") == [
        "KRW",
        "USD",
    ]
    assert _property_enum(tools["get_buying_power"].inputSchema, "currency") == ["KRW", "USD"]


async def test_live_order_tools_require_explicit_opt_in() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    default_server = create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))
    live_server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            live_order_required_scopes=("tossinvest:trade",),
        )
    )

    default_tool_names = {tool.name for tool in await default_server.list_tools()}
    live_tools = {tool.name: tool for tool in await live_server.list_tools()}

    assert {"create_order", "modify_order", "cancel_order"}.isdisjoint(default_tool_names)
    assert {"create_order", "modify_order", "cancel_order"} <= live_tools.keys()
    assert live_tools["create_order"].annotations is not None
    assert live_tools["create_order"].annotations.readOnlyHint is False
    assert live_tools["create_order"].annotations.destructiveHint is True
    assert live_tools["create_order"].annotations.idempotentHint is False


async def test_live_order_tools_allow_stdio_opt_in_without_oauth_scope() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            allow_stdio_live_orders=True,
        )
    )
    tool_names = {tool.name for tool in await server.list_tools()}

    assert {"create_order", "modify_order", "cancel_order"} <= tool_names
    assert _authorize_live_order((), allow_local_live_orders=True) == "local-stdio"


async def test_live_order_confirmation_registers_confirm_tool() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            allow_stdio_live_orders=True,
            require_live_order_confirmation=True,
        )
    )
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert "confirm_live_order" in tools
    assert tools["create_order"].annotations is not None
    assert tools["create_order"].annotations.destructiveHint is False
    assert tools["confirm_live_order"].annotations is not None
    assert tools["confirm_live_order"].annotations.destructiveHint is True


async def test_live_order_confirmation_requires_confirm_before_sdk_call() -> None:
    pytest.importorskip("mcp.server.fastmcp")
    client = _ConfirmClient()
    server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            account="7",
            enable_live_orders=True,
            allow_stdio_live_orders=True,
            require_live_order_confirmation=True,
        ),
        client_factory=cast(ClientContextFactory, lambda: _ConfirmClientContext(client)),
    )

    _, pending_raw = await server.call_tool(
        "create_order",
        {
            "symbol": "005930",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": "1",
            "price": "72000",
        },
    )
    pending = cast(dict[str, object], pending_raw)
    pending_summary = cast(dict[str, object], pending["summary"])

    assert pending["status"] == "pending_confirmation"
    assert pending["action"] == "create_order"
    assert pending_summary["account_seq"] == "7"
    assert client.orders.created_request is None

    _, confirmed_raw = await server.call_tool(
        "confirm_live_order",
        {"confirmation_id": pending["confirmationId"]},
    )
    confirmed = cast(dict[str, object], confirmed_raw)

    assert confirmed == {"orderId": "order-1"}
    assert client.orders.account == "7"
    assert client.orders.created_request is not None
    assert client.orders.created_request.model_dump(exclude_none=True) == {
        "symbol": "005930",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": "1",
        "price": "72000",
    }


async def test_live_order_tool_schemas_expose_sdk_enums() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            live_order_required_scopes=("tossinvest:trade",),
        )
    )
    tools = {tool.name: tool for tool in await server.list_tools()}

    create_order_schema = tools["create_order"].inputSchema
    assert _property_enum(create_order_schema, "side") == ["BUY", "SELL"]
    assert _property_enum(create_order_schema, "order_type") == ["LIMIT", "MARKET"]
    assert _property_enum(create_order_schema, "time_in_force") == ["DAY", "CLS"]
    assert "account_seq" in create_order_schema["properties"]


async def test_live_order_tool_call_requires_oauth_scope() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestRemoteServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            live_order_required_scopes=("tossinvest:trade",),
        )
    )

    with pytest.raises(Exception, match="OAuth access token"):
        await server.call_tool("cancel_order", {"order_id": "order-1"})


def test_live_order_scope_check_rejects_missing_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        server_module,
        "get_access_token",
        lambda: AccessToken(token="token", client_id="client", scopes=["tossinvest:read"]),
    )

    with pytest.raises(PermissionError, match="tossinvest:trade"):
        _require_oauth_scopes(("tossinvest:trade",))


def test_live_order_scope_check_accepts_configured_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        server_module,
        "get_access_token",
        lambda: AccessToken(
            token="token",
            client_id="client",
            scopes=["tossinvest:read", "tossinvest:trade"],
        ),
    )

    _require_oauth_scopes(("tossinvest:trade",))


def test_live_order_tools_require_configured_scope() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    with pytest.raises(TossInvestMCPRemoteConfigError, match="live-order-required-scope"):
        create_server(
            TossInvestRemoteServerConfig(
                "client-id",
                "client-secret",
                enable_live_orders=True,
            )
        )


def test_scope_metadata_merging_preserves_order_and_removes_duplicates() -> None:
    assert _merged_scopes(
        ("tossinvest:read", "profile"),
        ("tossinvest:trade", "tossinvest:read"),
    ) == ["tossinvest:read", "profile", "tossinvest:trade"]


def test_server_instructions_are_self_contained() -> None:
    assert len(SERVER_INSTRUCTIONS) <= 512
    assert "read-only" in SERVER_INSTRUCTIONS
    assert "investment advice" in SERVER_INSTRUCTIONS
    assert "accountSeq" in SERVER_INSTRUCTIONS
