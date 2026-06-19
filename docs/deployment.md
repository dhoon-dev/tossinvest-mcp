# Deployment

## Single-User Personal Server

Single-user mode is the milestone-1 default. One TossInvest credential set is
configured server-wide. ChatGPT and Codex clients share that configured account
context.

Anyone who can access `/mcp` can access the configured account data. Public exposure
requires HTTPS and access control.

Recommended controls:

- reverse proxy authentication
- network allowlisting
- private tunnel for development
- optional static bearer-token checks for clients that can send headers

## Multi-User OAuth

Multi-user OAuth is not implemented in milestone 1. A complete implementation must:

- isolate credentials and sessions per user
- implement OAuth 2.1 according to OpenAI Apps SDK and MCP authorization guidance
- verify access tokens on every request
- map each authenticated user to the correct TossInvest credential or session
- store refresh tokens or user secrets only with an explicit secure storage design
- fail closed when OAuth is configured but incomplete

## Internal HTTP

Run the app behind infrastructure that handles TLS:

```text
https://your-domain.example/mcp     -> http://app:8000/mcp
https://your-domain.example/healthz -> http://app:8000/healthz
```

For local development, bind to `127.0.0.1`. Use `0.0.0.0` only for containers or
reverse proxy deployments where exposure is intentional.
