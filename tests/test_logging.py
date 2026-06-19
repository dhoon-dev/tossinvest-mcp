from __future__ import annotations

from tossinvest_mcp_remote.logging import REDACTED, redact_mapping, redact_text


def test_redact_text_removes_bearer_token() -> None:
    assert redact_text("Authorization: Bearer secret-token") == f"Authorization: Bearer {REDACTED}"


def test_redact_mapping_removes_sensitive_values() -> None:
    assert redact_mapping({"authorization": "Bearer secret", "x-request-id": "req-1"}) == {
        "authorization": REDACTED,
        "x-request-id": "req-1",
    }
