from __future__ import annotations

import asyncio
import json

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.server import create_server


async def main() -> None:
    server = create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))
    tools = await server.list_tools()
    print(json.dumps([tool.name for tool in tools], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
