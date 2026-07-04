"""Exception hierarchy for the TossInvest MCP server."""

from __future__ import annotations


class TossInvestMCPError(Exception):
    """Base class for TossInvest MCP server exceptions."""


class TossInvestMCPConfigError(TossInvestMCPError):
    """Raised when server configuration is invalid."""


class CredentialHelperError(TossInvestMCPConfigError):
    """Raised when a credential helper cannot return a usable credential."""


class AccountResolutionError(TossInvestMCPError):
    """Raised when an account number cannot be resolved to accountSeq."""
