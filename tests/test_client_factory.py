from __future__ import annotations

from tossinvest_mcp.config import TossInvestMCPServerConfig


def test_client_factory_uses_account_seq_directly() -> None:
    config = TossInvestMCPServerConfig(
        client_id="client-id",
        client_secret="client-secret",
        account="7",
    )

    with config.create_client() as client:
        assert client.config.default_account == "7"
