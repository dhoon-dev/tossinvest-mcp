from __future__ import annotations

import pytest

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.errors import UnsupportedLiveOrderModeError
from tossinvest_mcp_remote.server import SERVER_INSTRUCTIONS, create_server


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


def test_live_order_tools_are_not_implemented() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    with pytest.raises(UnsupportedLiveOrderModeError):
        create_server(
            TossInvestRemoteServerConfig(
                "client-id",
                "client-secret",
                enable_live_orders=True,
            )
        )


def test_server_instructions_are_self_contained() -> None:
    assert len(SERVER_INSTRUCTIONS) <= 512
    assert "read-only" in SERVER_INSTRUCTIONS
    assert "investment advice" in SERVER_INSTRUCTIONS
    assert "accountSeq" in SERVER_INSTRUCTIONS
