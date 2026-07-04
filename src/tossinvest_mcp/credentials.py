"""Credential helper support for launch layers."""

from __future__ import annotations

import os
import shlex
import subprocess

from .errors import CredentialHelperError

DEFAULT_CREDENTIAL_HELPER_TIMEOUT = 5.0


def resolve_credential(
    value: str | None,
    command_line: str | None,
    *,
    label: str,
    env_var: str | None = None,
    timeout: float = DEFAULT_CREDENTIAL_HELPER_TIMEOUT,
) -> str:
    """Resolve a credential from an explicit value, helper command, or environment."""
    if value is not None:
        return _require_non_empty(value, label)
    if command_line is not None:
        return _run_credential_helper(command_line, label=label, timeout=timeout)
    if env_var is not None:
        env_value = os.getenv(env_var)
        if env_value:
            return _require_non_empty(env_value, label)
    raise CredentialHelperError(f"Missing TossInvest {label}.")


def resolve_optional_secret(
    value: str | None,
    command_line: str | None,
    *,
    label: str,
    env_var: str | None = None,
    timeout: float = DEFAULT_CREDENTIAL_HELPER_TIMEOUT,
) -> str | None:
    """Resolve an optional secret from explicit value, helper command, or environment."""
    if value is None and command_line is None and env_var is not None and not os.getenv(env_var):
        return None
    return resolve_credential(value, command_line, label=label, env_var=env_var, timeout=timeout)


def _run_credential_helper(command_line: str, *, label: str, timeout: float) -> str:
    try:
        command = shlex.split(command_line)
    except ValueError as exc:
        raise CredentialHelperError(
            f"TossInvest {label} credential helper command could not be parsed."
        ) from exc

    if not command:
        raise CredentialHelperError(
            f"TossInvest {label} credential helper command must not be empty."
        )

    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CredentialHelperError(
            f"TossInvest {label} credential helper timed out after {timeout:g} seconds."
        ) from exc
    except OSError as exc:
        raise CredentialHelperError(
            f"TossInvest {label} credential helper could not be started."
        ) from exc

    if completed.returncode != 0:
        raise CredentialHelperError(
            f"TossInvest {label} credential helper failed with exit status {completed.returncode}."
        )

    return _require_non_empty(completed.stdout.strip(), label)


def _require_non_empty(value: str, label: str) -> str:
    credential = value.strip()
    if not credential:
        raise CredentialHelperError(f"TossInvest {label} credential is empty.")
    return credential
