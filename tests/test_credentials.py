from __future__ import annotations

import shlex
import sys

import pytest

from tossinvest_mcp.credentials import resolve_credential
from tossinvest_mcp.errors import CredentialHelperError


def _python_command(source: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(source)}"


def test_resolve_credential_uses_explicit_value() -> None:
    assert resolve_credential(" value ", None, label="client ID") == "value"


def test_resolve_credential_runs_helper_without_shell() -> None:
    command = _python_command("print('helper-client-id')")

    assert resolve_credential(None, command, label="client ID") == "helper-client-id"


def test_credential_helper_error_does_not_include_output() -> None:
    command = _python_command("print('leaked-secret'); raise SystemExit(2)")

    with pytest.raises(CredentialHelperError) as exc_info:
        resolve_credential(None, command, label="client secret")

    message = str(exc_info.value)
    assert "client secret" in message
    assert "leaked-secret" not in message


def test_credential_helper_timeout() -> None:
    command = _python_command("import time; time.sleep(2)")

    with pytest.raises(CredentialHelperError) as exc_info:
        resolve_credential(None, command, label="client ID", timeout=0.01)

    assert "timed out" in str(exc_info.value)
