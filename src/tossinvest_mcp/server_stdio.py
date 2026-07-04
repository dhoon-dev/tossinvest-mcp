"""STDIO MCP transport entrypoint."""

from __future__ import annotations

from .config import TossInvestMCPServerConfig
from .server import create_server


def run_stdio(config: TossInvestMCPServerConfig) -> None:
    """Run the MCP server over STDIO."""
    create_server(config).run(transport="stdio")
