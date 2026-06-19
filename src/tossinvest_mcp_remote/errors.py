"""Exception hierarchy for the remote MCP server."""

from __future__ import annotations


class TossInvestMCPRemoteError(Exception):
    """Base class for remote MCP server exceptions."""


class TossInvestMCPRemoteConfigError(TossInvestMCPRemoteError):
    """Raised when server configuration is invalid."""


class CredentialHelperError(TossInvestMCPRemoteConfigError):
    """Raised when a credential helper cannot return a usable credential."""


class AccountResolutionError(TossInvestMCPRemoteError):
    """Raised when an account number cannot be resolved to accountSeq."""


class UnsupportedLiveOrderModeError(TossInvestMCPRemoteConfigError):
    """Raised when live-order tools are requested before implementation."""
