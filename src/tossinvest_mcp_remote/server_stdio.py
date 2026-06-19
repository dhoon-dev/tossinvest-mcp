"""STDIO MCP transport entrypoint."""

from __future__ import annotations

from .config import TossInvestRemoteServerConfig
from .server import create_server


def run_stdio(config: TossInvestRemoteServerConfig) -> None:
    """Run the MCP server over STDIO."""
    create_server(config).run(transport="stdio")
