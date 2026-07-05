from __future__ import annotations

from typing import cast

import pytest
from mcp.server.auth.provider import AccessToken

import tossinvest_mcp.server as server_module
from tossinvest_mcp.config import TossInvestMCPServerConfig
from tossinvest_mcp.errors import TossInvestMCPConfigError
from tossinvest_mcp.server import (
    _authorize_live_order,
    _require_oauth_scopes,
    _server_instructions,
    create_server,
)
from tossinvest_mcp.server_http import _merged_scopes


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


async def test_create_server_registers_read_only_tools_only() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestMCPServerConfig("client-id", "client-secret"))
    tool_names = {tool.name for tool in await server.list_tools()}

    assert "get_supported_openapi_version" in tool_names
    assert "get_latest_openapi_version" in tool_names
    assert "list_accounts" in tool_names
    assert "find_account_by_number" in tool_names
    assert "get_stock_comments" in tool_names
    assert "get_comment_replies" in tool_names
    assert "get_price" in tool_names
    assert "get_buying_power" in tool_names
    assert {"create_order", "modify_order", "cancel_order"}.isdisjoint(tool_names)


async def test_account_scoped_tool_schema_uses_account_seq() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestMCPServerConfig("client-id", "client-secret"))
    tools = {tool.name: tool for tool in await server.list_tools()}
    schema = tools["get_buying_power"].inputSchema

    assert "account_seq" in schema["properties"]
    assert "account" not in schema["properties"]
    assert "accountSeq" in schema["properties"]["account_seq"]["description"]
    assert "accountNo" in schema["properties"]["account_seq"]["description"]


async def test_read_only_tool_schemas_expose_sdk_enums() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestMCPServerConfig("client-id", "client-secret"))
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
    assert _property_enum(tools["get_stock_comments"].inputSchema, "sort") == [
        "POPULAR",
        "RECENT",
    ]
    assert _property_enum(tools["get_comment_replies"].inputSchema, "sort") == [
        "POPULAR",
        "NEWEST",
        "OLDEST",
    ]


async def test_openapi_version_tool_schemas_are_argument_free() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(TossInvestMCPServerConfig("client-id", "client-secret"))
    tools = {tool.name: tool for tool in await server.list_tools()}

    for tool_name in ("get_supported_openapi_version", "get_latest_openapi_version"):
        schema = tools[tool_name].inputSchema
        assert schema.get("properties") == {}
        assert schema.get("required", []) == []
        annotations = tools[tool_name].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is True


async def test_mcp_tool_descriptions_expose_rate_limit_groups() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestMCPServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            live_order_required_scopes=("tossinvest:trade",),
        )
    )
    tools = {tool.name: tool for tool in await server.list_tools()}
    expected_groups = {
        "list_accounts": "ACCOUNT",
        "find_account_by_number": "ACCOUNT",
        "get_stock": "STOCK",
        "get_stocks": "STOCK",
        "get_stock_warnings": "STOCK",
        "get_orderbook": "MARKET_DATA",
        "get_price": "MARKET_DATA",
        "get_prices": "MARKET_DATA",
        "get_trades": "MARKET_DATA",
        "get_price_limit": "MARKET_DATA",
        "get_candles": "MARKET_DATA_CHART",
        "get_exchange_rate": "MARKET_INFO",
        "get_kr_market_calendar": "MARKET_INFO",
        "get_us_market_calendar": "MARKET_INFO",
        "get_holdings": "ASSET",
        "list_orders": "ORDER_HISTORY",
        "get_order": "ORDER_HISTORY",
        "get_buying_power": "ORDER_INFO",
        "get_sellable_quantity": "ORDER_INFO",
        "get_commissions": "ORDER_INFO",
        "create_order": "ORDER",
        "modify_order": "ORDER",
        "cancel_order": "ORDER",
    }

    for tool_name, group in expected_groups.items():
        description = tools[tool_name].description or ""
        assert f"Rate limit group: {group}" in description
        assert "429" in description
        assert "Retry-After" in description
        assert "X-RateLimit-Reset" in description


async def test_live_order_tools_require_explicit_opt_in() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    default_server = create_server(TossInvestMCPServerConfig("client-id", "client-secret"))
    live_server = create_server(
        TossInvestMCPServerConfig(
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
        TossInvestMCPServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            allow_stdio_live_orders=True,
        )
    )
    tool_names = {tool.name for tool in await server.list_tools()}

    assert {"create_order", "modify_order", "cancel_order"} <= tool_names
    assert _authorize_live_order((), allow_local_live_orders=True) == "local-stdio"


async def test_live_order_tools_do_not_register_confirm_tool() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestMCPServerConfig(
            "client-id",
            "client-secret",
            enable_live_orders=True,
            allow_stdio_live_orders=True,
        )
    )
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert "confirm_live_order" not in tools
    assert tools["create_order"].annotations is not None
    assert tools["create_order"].annotations.destructiveHint is True


async def test_live_order_tool_schemas_expose_sdk_enums() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    server = create_server(
        TossInvestMCPServerConfig(
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
        TossInvestMCPServerConfig(
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

    with pytest.raises(TossInvestMCPConfigError, match="live-order-required-scope"):
        create_server(
            TossInvestMCPServerConfig(
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


def test_server_instructions_describe_read_only_mode() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    config = TossInvestMCPServerConfig("client-id", "client-secret")
    server = create_server(config)
    instructions = _server_instructions(config)

    assert server.instructions == instructions
    assert len(instructions) <= 512
    assert "live orders" not in instructions


def test_server_instructions_describe_live_order_mode() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    config = TossInvestMCPServerConfig(
        "client-id",
        "client-secret",
        enable_live_orders=True,
        live_order_required_scopes=("tossinvest:trade",),
    )
    server = create_server(config)
    instructions = _server_instructions(config)

    assert server.instructions == instructions
    assert len(instructions) <= 512
    assert "place, modify, or cancel live orders" in instructions
