"""Logging helpers with secret redaction."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping

REDACTED = "[REDACTED]"
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "authorization",
        "bearer",
        "client_id",
        "client_secret",
        "cookie",
        "password",
        "secret",
        "token",
        "x-api-key",
    }
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(client[_-]?secret['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"),
    re.compile(r"(?i)(access[_-]?token['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"),
)


def configure_logging(level: str = "INFO") -> None:
    """Configure process logging to stderr."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def redact_text(value: str) -> str:
    """Redact known secret patterns from free-form text."""
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(rf"\1{REDACTED}", redacted)
    return redacted


def redact_mapping(headers: Mapping[str, object]) -> dict[str, object]:
    """Return a copy of a mapping with sensitive values removed."""
    redacted: dict[str, object] = {}
    for key, value in headers.items():
        normalized = key.lower().replace("-", "_")
        if normalized in SENSITIVE_FIELD_NAMES or any(
            name in normalized for name in ("secret", "token")
        ):
            redacted[key] = REDACTED
        elif isinstance(value, str):
            redacted[key] = redact_text(value)
        else:
            redacted[key] = value
    return redacted
