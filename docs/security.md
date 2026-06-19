# Security

## Credential Handling

The package does not automatically read `.env` files. The CLI launch layer can read
environment variables and passes credentials explicitly into server configuration.

Prefer credential helper commands:

```bash
--client-id-command "/usr/bin/security find-generic-password -s tossinvest-api-key -w"
--client-secret-command "/usr/bin/security find-generic-password -s tossinvest-secret-key -w"
```

Helper commands are parsed with `shlex` and run without a shell. Stdout is trimmed and
used as the credential. Stdout, stderr, API keys, client secrets, bearer tokens,
authorization headers, cookies, and helper command output must not be logged.

## Access Control

The Streamable HTTP endpoint exposes user-specific financial data. Public deployments
must not be left unauthenticated. Use HTTPS and one or more access controls such as
reverse proxy auth, network allowlisting, private tunnels, or supported bearer-token
headers.

## Origin and Proxy Headers

Configure `--allowed-origin` when you want the app to enforce Origin checks on `/mcp`.
Configure `--trusted-proxy` before trusting `X-Forwarded-*` headers. Forwarded headers
from untrusted clients are ignored.

## OAuth TODO

Multi-user OAuth is not implemented. Do not silently share one server-wide TossInvest
credential set across multiple users. Future OAuth support must isolate credentials
and sessions per authenticated user.

## Financial Scope

This server is a data access layer. It does not provide investment advice, rank
securities, suggest trades, create portfolio allocations, or make buy/sell/hold
recommendations.

Live order tools are not included in milestone 1.
