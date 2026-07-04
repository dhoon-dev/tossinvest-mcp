# Changelog

## Unreleased

## 0.2.0

- Rename the package, CLI, and import package to `tossinvest-mcp`.

## 0.1.2

- Pin `tossinvest-openapi` to the v1.2.0 SDK release tag.
- Support the official TossInvest OpenAPI 1.1.5 schema modeled by the SDK.
- Drop the obsolete SDK `mcp` extra, which is no longer published in v1.2.0.
- Expose official OpenAPI version metadata as read-only MCP tools.
- Add SDK rate-limit group guidance to MCP tool descriptions.
- Align read-only MCP tool schemas with SDK request enums and defaults.

## 0.1.0

- Initial remote MCP server scaffold with STDIO and Streamable HTTP transports.
