"""Command-line interface for the TossInvest MCP remote server."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

from tossinvest import __version__ as tossinvest_sdk_version

from ._version import __version__
from .config import DEFAULT_ACCOUNT_CACHE_TTL, TossInvestRemoteServerConfig
from .credentials import (
    DEFAULT_CREDENTIAL_HELPER_TIMEOUT,
    resolve_credential,
    resolve_optional_secret,
)
from .errors import CredentialHelperError, TossInvestMCPRemoteConfigError
from .logging import configure_logging
from .server_http import HTTPServerConfig, run_http
from .server_stdio import run_stdio


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the TossInvest MCP remote server.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stdio_parser = subparsers.add_parser("stdio", help="Run MCP over STDIO.")
    _add_common_server_args(stdio_parser)

    http_parser = subparsers.add_parser("serve-http", help="Run MCP over Streamable HTTP.")
    _add_common_server_args(http_parser)
    http_parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host.")
    http_parser.add_argument("--port", default=8000, type=int, help="HTTP bind port.")
    http_parser.add_argument(
        "--trusted-proxy",
        action="append",
        default=[],
        help="Trusted reverse proxy IP or CIDR. May be passed more than once.",
    )
    http_parser.add_argument(
        "--allowed-origin",
        action="append",
        default=[],
        help="Allowed Origin for /mcp. May be passed more than once.",
    )
    http_bearer_group = http_parser.add_mutually_exclusive_group()
    http_bearer_group.add_argument(
        "--http-bearer-token",
        help="Static bearer token for HTTP clients that support Authorization headers.",
    )
    http_bearer_group.add_argument(
        "--http-bearer-token-command",
        help="Command that prints the HTTP bearer token to stdout.",
    )
    http_parser.add_argument("--log-level", default="info", help="uvicorn log level.")

    subparsers.add_parser("version", help="Print package and SDK version information.")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> TossInvestRemoteServerConfig:
    """Build server configuration from parsed arguments and environment."""
    client_id = resolve_credential(
        args.client_id,
        args.client_id_command,
        label="client ID",
        env_var="TOSSINVEST_CLIENT_ID",
        timeout=args.credential_helper_timeout,
    )
    client_secret = resolve_credential(
        args.client_secret,
        args.client_secret_command,
        label="client secret",
        env_var="TOSSINVEST_CLIENT_SECRET",
        timeout=args.credential_helper_timeout,
    )
    account_seq = args.account_seq or os.getenv("TOSSINVEST_ACCOUNT_SEQ")
    account_number = args.account_number or os.getenv("TOSSINVEST_ACCOUNT_NO")
    if account_seq and account_number:
        raise TossInvestMCPRemoteConfigError(
            "Use either accountSeq or accountNo, not both. "
            "Unset TOSSINVEST_ACCOUNT_SEQ or TOSSINVEST_ACCOUNT_NO if needed."
        )
    return TossInvestRemoteServerConfig(
        client_id=client_id,
        client_secret=client_secret,
        account=account_seq,
        account_number=account_number,
        base_url=args.base_url,
        timeout=args.timeout,
        max_retries=args.max_retries,
        user_agent=args.user_agent,
        account_cache_ttl=args.account_cache_ttl,
        mode=args.mode,
    )


def http_config_from_args(args: argparse.Namespace) -> HTTPServerConfig:
    """Build HTTP transport configuration from parsed arguments and environment."""
    bearer_token = resolve_optional_secret(
        args.http_bearer_token,
        args.http_bearer_token_command,
        label="HTTP bearer token",
        env_var="TOSSINVEST_MCP_BEARER_TOKEN",
        timeout=args.credential_helper_timeout,
    )
    return HTTPServerConfig(
        host=args.host,
        port=args.port,
        trusted_proxies=tuple(args.trusted_proxy),
        allowed_origins=tuple(args.allowed_origin),
        bearer_token=bearer_token,
        log_level=args.log_level,
    )


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    if args.command == "version":
        _print_version()
        return

    configure_logging(getattr(args, "log_level", "INFO"))
    try:
        config = config_from_args(args)
        if args.command == "stdio":
            run_stdio(config)
            return
        if args.command == "serve-http":
            run_http(config, http_config_from_args(args))
            return
    except (CredentialHelperError, TossInvestMCPRemoteConfigError) as exc:
        raise SystemExit(str(exc)) from exc

    raise SystemExit(f"Unsupported command: {args.command}")


def _add_common_server_args(parser: argparse.ArgumentParser) -> None:
    client_id_group = parser.add_mutually_exclusive_group()
    client_id_group.add_argument("--client-id", help="TossInvest OpenAPI OAuth client ID.")
    client_id_group.add_argument(
        "--client-id-command",
        help=(
            "Command that prints the TossInvest OpenAPI OAuth client ID to stdout. "
            "The command is parsed with shlex and is not run through a shell."
        ),
    )

    client_secret_group = parser.add_mutually_exclusive_group()
    client_secret_group.add_argument(
        "--client-secret",
        help="TossInvest OpenAPI OAuth client secret.",
    )
    client_secret_group.add_argument(
        "--client-secret-command",
        help=(
            "Command that prints the TossInvest OpenAPI OAuth client secret to stdout. "
            "The command is parsed with shlex and is not run through a shell."
        ),
    )

    parser.add_argument(
        "--credential-helper-timeout",
        default=DEFAULT_CREDENTIAL_HELPER_TIMEOUT,
        type=float,
        help="Credential helper timeout in seconds.",
    )
    account_group = parser.add_mutually_exclusive_group()
    account_group.add_argument(
        "--account",
        dest="account_number",
        help="Default TossInvest accountNo for account-scoped tools.",
    )
    account_group.add_argument(
        "--account-seq",
        help="Default TossInvest accountSeq for account-scoped tools.",
    )
    parser.add_argument(
        "--base-url",
        default="https://openapi.tossinvest.com",
        help="TossInvest OpenAPI base URL.",
    )
    parser.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--max-retries",
        default=2,
        type=int,
        help="Maximum retries for idempotent HTTP requests.",
    )
    parser.add_argument(
        "--user-agent",
        default="tossinvest-openapi tossinvest-mcp-remote/0.1.0",
        help="User-Agent header for TossInvest API requests.",
    )
    parser.add_argument(
        "--account-cache-ttl",
        default=DEFAULT_ACCOUNT_CACHE_TTL,
        type=float,
        help="Account list cache TTL in seconds.",
    )
    parser.add_argument(
        "--mode",
        choices=["single_user", "multi_user"],
        default="single_user",
        help="Authentication mode. Multi-user OAuth is reserved for a future milestone.",
    )


def _print_version() -> None:
    try:
        package_version = version("tossinvest-mcp-remote")
    except PackageNotFoundError:
        package_version = __version__
    sys.stdout.write(f"tossinvest-mcp-remote {package_version}\n")
    sys.stdout.write(f"tossinvest-openapi {tossinvest_sdk_version}\n")
