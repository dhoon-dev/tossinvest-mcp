# ChatGPT Apps and Connectors

Milestone 1 is a data-only MCP app for personal single-user deployments. It exposes
MCP tools only. It does not serve an iframe UI, widget resources, or custom UI
components.

## Endpoint

ChatGPT must be able to reach a public HTTPS URL that includes the MCP path:

```text
https://your-domain.example/mcp
```

The app itself may listen on internal HTTP. Terminate HTTPS and enforce public access
control in infrastructure:

```text
https://your-domain.example/mcp     -> http://app:8000/mcp
https://your-domain.example/healthz -> http://app:8000/healthz
```

## Setup

1. Enable developer mode if required by the current ChatGPT UI.
2. Open Settings -> Apps & Connectors or Settings -> Connectors.
3. Create a connector or app.
4. Enter a user-facing name.
5. Enter a short description.
6. Enter the public HTTPS `/mcp` endpoint.
7. Select the authentication option that matches your deployment.
8. Create the connector.
9. Verify that the expected read-only tool list appears.
10. Refresh metadata after changing tools or descriptions.

## Authentication Notes

This server does not implement multi-user OAuth yet. ChatGPT support is therefore
limited to personal single-user deployments unless you place an authenticated reverse
proxy or equivalent access-control layer in front of the app.

Do not claim static bearer-token authentication works with ChatGPT unless you verify it
against the current ChatGPT Apps/Connectors UI and documentation. For public exposure,
use HTTPS and access control.

## Safety Notes

The server exposes financial account and market data. It does not provide investment
advice and does not include live order tools in milestone 1.
