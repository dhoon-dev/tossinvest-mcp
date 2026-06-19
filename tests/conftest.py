from __future__ import annotations

from typing import Any

from pytest_httpx import HTTPXMock

BASE_URL = "https://openapi.tossinvest.com"
TOKEN_URL = f"{BASE_URL}/oauth2/token"


def add_token_response(
    httpx_mock: HTTPXMock,
    *,
    token: str = "access-token",
    expires_in: int = 3600,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=TOKEN_URL,
        json={"access_token": token, "token_type": "Bearer", "expires_in": expires_in},
    )


def add_api_response(httpx_mock: HTTPXMock, *, method: str, url: str, result: Any) -> None:
    httpx_mock.add_response(method=method, url=url, json={"result": result})


def account_payload(account_seq: int = 1) -> dict[str, object]:
    return {"accountNo": "12345678901", "accountSeq": account_seq, "accountType": "BROKERAGE"}


def holdings_payload() -> dict[str, object]:
    return {
        "totalPurchaseAmount": {"krw": "1000"},
        "marketValue": {"amount": {"krw": "1100"}, "amountAfterCost": {"krw": "1090"}},
        "profitLoss": {
            "amount": {"krw": "100"},
            "amountAfterCost": {"krw": "90"},
            "rate": "10",
            "rateAfterCost": "9",
        },
        "dailyProfitLoss": {"amount": {"krw": "10"}, "rate": "1"},
        "items": [],
    }
