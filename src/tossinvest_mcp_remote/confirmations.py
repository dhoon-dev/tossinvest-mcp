"""In-memory live order confirmation state."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Literal

LiveOrderAction = Literal["create_order", "modify_order", "cancel_order"]


@dataclass(frozen=True, slots=True)
class PendingLiveOrder:
    """A live order request waiting for explicit confirmation."""

    confirmation_id: str
    action: LiveOrderAction
    arguments: dict[str, object]
    summary: dict[str, object]
    authorization_key: str
    created_at: float
    expires_at: float


class LiveOrderConfirmationStore:
    """Store pending live order confirmations for one server process."""

    def __init__(
        self,
        *,
        ttl: float,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.ttl = ttl
        self._now = now
        self._pending: dict[str, PendingLiveOrder] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        action: LiveOrderAction,
        arguments: Mapping[str, object],
        summary: Mapping[str, object],
        authorization_key: str,
    ) -> dict[str, object]:
        """Create a confirmation and return a client-facing pending response."""
        now = self._now()
        expires_at = now + self.ttl
        confirmation_id = secrets.token_urlsafe(18)
        pending = PendingLiveOrder(
            confirmation_id=confirmation_id,
            action=action,
            arguments=dict(arguments),
            summary=dict(summary),
            authorization_key=authorization_key,
            created_at=now,
            expires_at=expires_at,
        )
        with self._lock:
            self._purge_expired_locked(now)
            self._pending[confirmation_id] = pending
        return _pending_response(pending)

    def pop(self, confirmation_id: str, *, authorization_key: str) -> PendingLiveOrder:
        """Return and remove a pending confirmation if it is valid for the caller."""
        now = self._now()
        with self._lock:
            self._purge_expired_locked(now)
            pending = self._pending.get(confirmation_id)
            if pending is None:
                msg = "Live order confirmation was not found, expired, or already used."
                raise ValueError(msg)
            if pending.authorization_key != authorization_key:
                msg = "Live order confirmation was created by a different caller."
                raise PermissionError(msg)
            del self._pending[confirmation_id]
        return pending

    def _purge_expired_locked(self, now: float) -> None:
        expired_ids = [
            confirmation_id
            for confirmation_id, pending in self._pending.items()
            if pending.expires_at <= now
        ]
        for confirmation_id in expired_ids:
            del self._pending[confirmation_id]


def _pending_response(pending: PendingLiveOrder) -> dict[str, object]:
    return {
        "status": "pending_confirmation",
        "confirmationId": pending.confirmation_id,
        "action": pending.action,
        "summary": pending.summary,
        "expiresAt": _utc_timestamp(pending.expires_at),
        "nextTool": "confirm_live_order",
    }


def _utc_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")
