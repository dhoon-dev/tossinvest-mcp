from __future__ import annotations

import pytest

from tossinvest_mcp.config import TossInvestMCPServerConfig
from tossinvest_mcp.server import create_server


def test_stdio_server_creation_does_not_write_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_server(TossInvestMCPServerConfig("client-id", "client-secret"))

    captured = capsys.readouterr()
    assert captured.out == ""
