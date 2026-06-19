from __future__ import annotations

import pytest

from tossinvest_mcp_remote.config import TossInvestRemoteServerConfig
from tossinvest_mcp_remote.server import create_server


def test_stdio_server_creation_does_not_write_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    create_server(TossInvestRemoteServerConfig("client-id", "client-secret"))

    captured = capsys.readouterr()
    assert captured.out == ""
