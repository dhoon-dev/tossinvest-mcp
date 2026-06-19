"""Account lookup helpers."""

from __future__ import annotations

from collections.abc import Iterable

from tossinvest import Account, TossInvestValidationError


def find_account_by_number(accounts: Iterable[Account], account_no: str) -> Account:
    """Return the account matching an official accountNo."""
    for account in accounts:
        if account.account_no == account_no:
            return account
    raise TossInvestValidationError("No TossInvest account found for the requested accountNo.")
