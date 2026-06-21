from __future__ import annotations

import pytest

from tossinvest_mcp_remote.confirmations import LiveOrderConfirmationStore


def test_live_order_confirmation_store_returns_pending_response() -> None:
    now = 100.0
    store = LiveOrderConfirmationStore(ttl=60, now=lambda: now)

    response = store.create(
        action="create_order",
        arguments={"symbol": "005930"},
        summary={"symbol": "005930"},
        authorization_key="caller",
    )

    assert response["status"] == "pending_confirmation"
    assert response["action"] == "create_order"
    assert response["summary"] == {"symbol": "005930"}
    assert response["nextTool"] == "confirm_live_order"

    pending = store.pop(str(response["confirmationId"]), authorization_key="caller")

    assert pending.action == "create_order"
    assert pending.arguments == {"symbol": "005930"}


def test_live_order_confirmation_store_rejects_different_caller() -> None:
    store = LiveOrderConfirmationStore(ttl=60, now=lambda: 100.0)
    response = store.create(
        action="cancel_order",
        arguments={"order_id": "order-1"},
        summary={"order_id": "order-1"},
        authorization_key="caller-1",
    )

    with pytest.raises(PermissionError, match="different caller"):
        store.pop(str(response["confirmationId"]), authorization_key="caller-2")


def test_live_order_confirmation_store_expires_pending_items() -> None:
    now = 100.0
    store = LiveOrderConfirmationStore(ttl=10, now=lambda: now)
    response = store.create(
        action="cancel_order",
        arguments={"order_id": "order-1"},
        summary={"order_id": "order-1"},
        authorization_key="caller",
    )

    now = 111.0

    with pytest.raises(ValueError, match="expired"):
        store.pop(str(response["confirmationId"]), authorization_key="caller")
