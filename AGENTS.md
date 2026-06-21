# AGENTS.md

## Project Scope

This repository provides an unofficial remote MCP server for the TossInvest OpenAPI SDK.
It is a transport and tool-registration layer, not a replacement SDK.

Generated source, documentation, comments, test names, and commit-facing text in this
repository must be written in English unless a user explicitly asks for a translation.

## Sources of Truth

- Prefer public TossInvest SDK APIs such as `TossInvestClient`, `AsyncTossInvestClient`,
  public models, and public resource groups.
- Do not import `tossinvest._mcp.*` from production code.
- Keep the structure and engineering style close to `dhoon-dev/tossinvest-openapi`.
- Account-scoped APIs require `accountSeq`, not `accountNo`. Resolve `accountNo` lazily
  only when an account-scoped tool first needs it.
- Preserve read-only default behavior. Do not implement live order tools without an
  explicit scope change.

## Dependency and Tooling Rules

- Use Python 3.12+.
- Use `uv` for project commands.
- Before changing behavior that depends on third-party packages, consult current
  documentation.
- Keep STDIO stdout protocol-clean. Diagnostics and logs must go to stderr.

## Repo-Local Codex Skills

- Use `$toss-bump-version` for release version bumps.
- Use `$toss-commit-changes` when staging and creating commits in this repo.

## Quality Gate

Run the focused command for the change first. Before handing off broad changes,
run the full local gate:

```bash
uv lock
uv sync --locked --all-extras --group docs
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest -m "not live"
uv run --locked --group docs sphinx-build -W -b html docs docs/_build/html
uv build
```

## Credentials and Security

- The server package must not automatically read `.env` files.
- Launch layers may read environment variables and pass values into typed config objects.
- Never log secrets, authorization headers, bearer tokens, cookies, credential-helper
  stdout, API keys, or client secrets.
- Keep `.env.example` values empty.
- Public HTTP deployments require HTTPS and access control outside or in front of this app.

## Commit Messages

- Use Conventional Commits-style titles:
  - `feat: add remote MCP server`
  - `fix: preserve account cache TTL`
  - `chore: update CI workflow`
- Write a title, then one blank line, then a body:

```text
fix: preserve default live API base URL

Ensure empty optional CI variables do not override the SDK default base URL
during live tests.
```

- Use these default types:
  - `feat` for user-visible server features or supported API additions.
  - `fix` for bug fixes, schema corrections, and behavioral regressions.
  - `chore` for tooling, CI, dependency, repository, or maintenance changes.
  - `docs` for documentation-only changes.
  - `test` for test-only changes.
  - `refactor` for internal code changes that do not alter behavior.
  - `ci` for GitHub Actions and CI configuration changes.
- Keep the title in English, concise, specific, and no longer than 50 characters.
- Wrap body lines at 72 characters or fewer. Use the body to explain the
  reason, impact, or notable verification for the change.
- Follow the repository rules enforced by `scripts/check_commit_messages.py`.
- Never bypass the commit hook with `--no-verify`.
