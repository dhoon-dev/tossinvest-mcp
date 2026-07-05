"""Shared MCP server creation and tool registration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.types import ToolAnnotations
from pydantic import Field
from tossinvest import (
    CandleInterval,
    CurrencyCode,
    OrderListStatus,
    OrderSide,
    OrderTimeInForce,
    OrderType,
)
from tossinvest_extensions import CommentSortType, ReplySortType

from .client_factory import ClientContextFactory
from .config import TossInvestMCPServerConfig
from .errors import TossInvestMCPConfigError
from .tools import TossInvestMCPTools

if TYPE_CHECKING:
    from mcp.server.auth.provider import AccessToken, TokenVerifier
    from mcp.server.auth.settings import AuthSettings
    from mcp.server.fastmcp import FastMCP

ACCOUNT_SEQ_DESCRIPTION = (
    "Optional accountSeq override. Omit when the server was started with --account or "
    "--account-seq. Use accountSeq as account_seq for overrides, not accountNo."
)
ACCOUNT_NO_DESCRIPTION = (
    "Official accountNo from list_accounts. Resolving accountNo calls the ACCOUNT-rate-limited "
    "accounts endpoint."
)
READ_ONLY_SERVER_INSTRUCTIONS = (
    "Use this TossInvest OpenAPI MCP server to read API metadata, discover accounts, inspect "
    "stocks, retrieve market data and market information, read stock community comments, and "
    "view account-scoped information."
)
LIVE_ORDER_SERVER_INSTRUCTIONS = (
    "Use this TossInvest OpenAPI MCP server to read API metadata, discover accounts, inspect "
    "stocks, retrieve market data and market information, read stock community comments, view "
    "account-scoped information, and place, modify, or cancel live orders."
)
READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True)
LIVE_ORDER_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)


def create_server(
    config: TossInvestMCPServerConfig,
    *,
    client_factory: ClientContextFactory | None = None,
    auth: AuthSettings | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastMCP:
    """Create a TossInvest MCP server."""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    if (
        config.enable_live_orders
        and not config.allow_stdio_live_orders
        and not config.live_order_required_scopes
    ):
        raise TossInvestMCPConfigError(
            "Live order tools require at least one --live-order-required-scope "
            "or --allow-stdio-live-orders."
        )

    tools = TossInvestMCPTools(
        client_factory or config.create_client,
        extensions_client_factory=config.create_extensions_client,
        account_resolver=config.account_seq_for_tool,
        account_list_cache_getter=config.cached_account_list,
        account_list_observer=config.cache_account_list,
    )
    server = FastMCP(
        name="TossInvest MCP",
        instructions=_server_instructions(config),
        stateless_http=True,
        auth=auth,
        token_verifier=token_verifier,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    _register_openapi_tools(server, tools)
    _register_account_tools(server, tools)
    _register_stock_tools(server, tools)
    _register_community_tools(server, tools)
    _register_market_data_tools(server, tools)
    _register_market_info_tools(server, tools)
    _register_account_scoped_tools(server, tools)
    if config.enable_live_orders:
        _register_live_order_tools(
            server,
            tools,
            required_scopes=config.live_order_required_scopes,
            allow_local_live_orders=config.allow_stdio_live_orders,
        )
    return server


def _server_instructions(config: TossInvestMCPServerConfig) -> str:
    """Return server instructions that match the registered tool surface."""
    if config.enable_live_orders:
        return LIVE_ORDER_SERVER_INSTRUCTIONS
    return READ_ONLY_SERVER_INSTRUCTIONS


def _register_openapi_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register official OpenAPI version metadata tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_supported_openapi_version() -> str:
        """Return the official OpenAPI version modeled by this SDK release."""
        return tools.get_supported_openapi_version()

    @server.tool(annotations=read_only_annotations)
    def get_latest_openapi_version() -> str:
        """Fetch and return the latest official TossInvest OpenAPI version.

        This calls /openapi-docs/latest/openapi.json without OAuth.
        """
        return tools.get_latest_openapi_version()


def _register_account_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register account lookup tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def list_accounts() -> list[dict[str, object]]:
        """List accounts only when account discovery is needed.

        Rate limit group: ACCOUNT. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.list_accounts()

    @server.tool(annotations=read_only_annotations)
    def find_account_by_number(
        account_no: str = Field(description=ACCOUNT_NO_DESCRIPTION),
    ) -> dict[str, object]:
        """Return the account matching accountNo, including its accountSeq.

        Rate limit group: ACCOUNT. On 429, respect Retry-After or X-RateLimit-Reset.
        Prefer a configured accountSeq when it is already known.
        """
        return tools.find_account_by_number(account_no)


def _register_stock_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register stock information tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_stock(symbol: str) -> dict[str, object]:
        """Return one stock master record.

        Rate limit group: STOCK. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_stock(symbol)

    @server.tool(annotations=read_only_annotations)
    def get_stocks(symbols: list[str]) -> list[dict[str, object]]:
        """Return stock master records for one or more symbols.

        Rate limit group: STOCK. On 429, respect Retry-After or X-RateLimit-Reset.
        Prefer one batched call over repeated single-symbol calls.
        """
        return tools.get_stocks(symbols)

    @server.tool(annotations=read_only_annotations)
    def get_stock_warnings(symbol: str) -> list[dict[str, object]]:
        """Return trading warnings for a symbol.

        Rate limit group: STOCK. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_stock_warnings(symbol)


def _register_community_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register unofficial TossInvest web community tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_stock_comments(
        stock_code: str,
        sort: CommentSortType = "POPULAR",
        cursor: int | str | None = None,
        count: int | None = None,
    ) -> dict[str, object]:
        """Return stock community comments for a TossInvest stock page.

        Unofficial TossInvest web community API. On 429, respect Retry-After or
        X-RateLimit-Reset. `stock_code` accepts common codes and symbols such as
        000660 or AAPL.
        """
        return tools.get_stock_comments(
            stock_code,
            sort=sort,
            cursor=cursor,
            count=count,
        )

    @server.tool(annotations=read_only_annotations)
    def get_comment_replies(
        comment_id: int | str,
        sort: ReplySortType = "POPULAR",
        cursor: int | str | None = None,
        last_like_count: int | None = None,
    ) -> dict[str, object]:
        """Return replies for a TossInvest community comment.

        Unofficial TossInvest web community API. On 429, respect Retry-After or
        X-RateLimit-Reset. `comment_id` is a parent comment identifier returned
        by get_stock_comments. For pagination, pass `key` as `cursor`; when
        available, pass the last reply's `statistic.likeCount` as
        `last_like_count`.
        """
        return tools.get_comment_replies(
            comment_id,
            sort=sort,
            cursor=cursor,
            last_like_count=last_like_count,
        )


def _register_market_data_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register market data tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_orderbook(symbol: str) -> dict[str, object]:
        """Return the current orderbook for a symbol.

        Rate limit group: MARKET_DATA. On 429, respect Retry-After or X-RateLimit-Reset.
        Avoid tight polling loops.
        """
        return tools.get_orderbook(symbol)

    @server.tool(annotations=read_only_annotations)
    def get_price(symbol: str) -> dict[str, object]:
        """Return the current price for one symbol.

        Rate limit group: MARKET_DATA. On 429, respect Retry-After or X-RateLimit-Reset.
        Avoid tight polling loops.
        """
        return tools.get_price(symbol)

    @server.tool(annotations=read_only_annotations)
    def get_prices(symbols: list[str]) -> list[dict[str, object]]:
        """Return current prices for one or more symbols.

        Rate limit group: MARKET_DATA. On 429, respect Retry-After or X-RateLimit-Reset.
        Prefer one batched call over repeated single-symbol calls.
        """
        return tools.get_prices(symbols)

    @server.tool(annotations=read_only_annotations)
    def get_trades(symbol: str, count: int | None = None) -> list[dict[str, object]]:
        """Return recent trades for a symbol.

        Rate limit group: MARKET_DATA. On 429, respect Retry-After or X-RateLimit-Reset.
        Avoid tight polling loops.
        """
        return tools.get_trades(symbol, count=count)

    @server.tool(annotations=read_only_annotations)
    def get_price_limit(symbol: str) -> dict[str, object]:
        """Return upper and lower price limits for a symbol.

        Rate limit group: MARKET_DATA. On 429, respect Retry-After or X-RateLimit-Reset.
        Avoid tight polling loops.
        """
        return tools.get_price_limit(symbol)

    @server.tool(annotations=read_only_annotations)
    def get_candles(
        symbol: str,
        interval: CandleInterval,
        *,
        count: int | None = None,
        before: str | None = None,
        adjusted: bool | None = None,
    ) -> dict[str, object]:
        """Return candle data for a symbol and interval.

        Rate limit group: MARKET_DATA_CHART. On 429, respect Retry-After or
        X-RateLimit-Reset. Avoid tight polling loops.
        """
        return tools.get_candles(
            symbol,
            interval=interval,
            count=count,
            before=before,
            adjusted=adjusted,
        )


def _register_market_info_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register market information tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_exchange_rate(
        base_currency: CurrencyCode,
        quote_currency: CurrencyCode,
        date_time: str | None = None,
    ) -> dict[str, object]:
        """Return an exchange rate between two supported currencies.

        Rate limit group: MARKET_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_exchange_rate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            date_time=date_time,
        )

    @server.tool(annotations=read_only_annotations)
    def get_kr_market_calendar(date: str | None = None) -> dict[str, object]:
        """Return Korean market calendar information.

        Rate limit group: MARKET_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_kr_market_calendar(date=date)

    @server.tool(annotations=read_only_annotations)
    def get_us_market_calendar(date: str | None = None) -> dict[str, object]:
        """Return US market calendar information.

        Rate limit group: MARKET_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_us_market_calendar(date=date)


def _register_account_scoped_tools(server: FastMCP, tools: TossInvestMCPTools) -> None:
    """Register read-only account-scoped tools."""
    read_only_annotations = READ_ONLY_TOOL_ANNOTATIONS

    @server.tool(annotations=read_only_annotations)
    def get_holdings(
        symbol: str | None = None,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Return holdings using the configured default accountSeq or an account_seq override.

        Rate limit group: ASSET. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_holdings(symbol=symbol, account_seq=account_seq)

    @server.tool(annotations=read_only_annotations)
    def list_orders(
        status: OrderListStatus = "OPEN",
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """List orders using the configured default accountSeq or an account_seq override.

        Rate limit group: ORDER_HISTORY. On 429, respect Retry-After or
        X-RateLimit-Reset. Prefer status=OPEN when only active orders are needed.
        """
        return tools.list_orders(
            status=status,
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            cursor=cursor,
            limit=limit,
            account_seq=account_seq,
        )

    @server.tool(annotations=read_only_annotations)
    def get_order(
        order_id: str,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Return one order using the configured default accountSeq or an account_seq override.

        Rate limit group: ORDER_HISTORY. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_order(order_id, account_seq=account_seq)

    @server.tool(annotations=read_only_annotations)
    def get_buying_power(
        currency: CurrencyCode,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Return cash buying power using the configured default accountSeq or an override.

        Rate limit group: ORDER_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_buying_power(currency=currency, account_seq=account_seq)

    @server.tool(annotations=read_only_annotations)
    def get_sellable_quantity(
        symbol: str,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Return sellable quantity using the configured default accountSeq or an override.

        Rate limit group: ORDER_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_sellable_quantity(symbol=symbol, account_seq=account_seq)

    @server.tool(annotations=read_only_annotations)
    def get_commissions(
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> list[dict[str, object]]:
        """Return commissions using the configured default accountSeq or an account_seq override.

        Rate limit group: ORDER_INFO. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        return tools.get_commissions(account_seq=account_seq)


def _register_live_order_tools(
    server: FastMCP,
    tools: TossInvestMCPTools,
    *,
    required_scopes: Sequence[str],
    allow_local_live_orders: bool,
) -> None:
    """Register live order tools that execute immediately after authorization."""

    @server.tool(annotations=LIVE_ORDER_TOOL_ANNOTATIONS)
    def create_order(
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        *,
        quantity: str | None = None,
        order_amount: str | None = None,
        price: str | None = None,
        time_in_force: OrderTimeInForce | None = None,
        client_order_id: str | None = None,
        confirm_high_value_order: bool | None = None,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Submit a live order using the configured default accountSeq or an override.

        Rate limit group: ORDER. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        _authorize_live_order(required_scopes, allow_local_live_orders=allow_local_live_orders)
        return tools.create_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            order_amount=order_amount,
            price=price,
            time_in_force=time_in_force,
            client_order_id=client_order_id,
            confirm_high_value_order=confirm_high_value_order,
            account_seq=account_seq,
        )

    @server.tool(annotations=LIVE_ORDER_TOOL_ANNOTATIONS)
    def modify_order(
        order_id: str,
        order_type: OrderType,
        *,
        quantity: str | None = None,
        price: str | None = None,
        confirm_high_value_order: bool | None = None,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Modify a live order using the configured default accountSeq or an override.

        Rate limit group: ORDER. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        _authorize_live_order(required_scopes, allow_local_live_orders=allow_local_live_orders)
        return tools.modify_order(
            order_id,
            order_type=order_type,
            quantity=quantity,
            price=price,
            confirm_high_value_order=confirm_high_value_order,
            account_seq=account_seq,
        )

    @server.tool(annotations=LIVE_ORDER_TOOL_ANNOTATIONS)
    def cancel_order(
        order_id: str,
        account_seq: str | None = Field(default=None, description=ACCOUNT_SEQ_DESCRIPTION),
    ) -> dict[str, object]:
        """Cancel a live order using the configured default accountSeq or an override.

        Rate limit group: ORDER. On 429, respect Retry-After or X-RateLimit-Reset.
        """
        _authorize_live_order(required_scopes, allow_local_live_orders=allow_local_live_orders)
        return tools.cancel_order(order_id, account_seq=account_seq)


def _authorize_live_order(
    required_scopes: Sequence[str],
    *,
    allow_local_live_orders: bool,
) -> str:
    """Authorize one live order tool call."""
    if allow_local_live_orders:
        return "local-stdio"
    access_token = _require_oauth_scopes(required_scopes)
    return _access_token_authorization_key(access_token)


def _require_oauth_scopes(required_scopes: Sequence[str]) -> AccessToken:
    """Require the current OAuth access token to contain every configured scope."""
    access_token = get_access_token()
    if access_token is None:
        msg = "Live order tools require an OAuth access token."
        raise PermissionError(msg)
    granted_scopes = set(access_token.scopes)
    missing_scopes = [scope for scope in required_scopes if scope not in granted_scopes]
    if missing_scopes:
        msg = "Live order tools require OAuth scope(s): " + ", ".join(missing_scopes)
        raise PermissionError(msg)
    return access_token


def _access_token_authorization_key(access_token: AccessToken) -> str:
    subject = access_token.subject or ""
    resource = access_token.resource or ""
    return f"oauth:{access_token.client_id}:{subject}:{resource}"
