---
name: toss-commit-changes
description: Repository-specific workflow for creating Git commits in tossinvest-mcp-remote. Use when the user asks Codex to commit changes, stage files, write a commit message, amend a commit, or verify commit-message compliance in this repo.
---

# Toss Commit Changes

## Workflow

1. Inspect the tree and identify intended files:

```bash
git status --short --branch
git diff --name-status
```

2. Stage only files related to the user's request. Do not stage unrelated user changes.

3. Write a Conventional Commits message that follows this repo's rules:

- Allowed types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `ci`.
- Title format: `<type>: <summary>` or `<type>(scope): <summary>`.
- Title length: 50 characters or fewer.
- Body required after one blank line.
- Body lines: 72 characters or fewer.
- English only unless the user explicitly requests translation.

4. Let the local `commit-msg` hook run if configured. Never bypass it with
   `--no-verify`. If the hook fails, fix the message and retry.

5. After commit, verify:

```bash
uv run --locked python scripts/check_commit_messages.py --range HEAD^..HEAD
git status --short --branch
git show --stat --oneline --no-renames HEAD
```

6. Report the new commit hash and title.

## Message Examples

```text
ci: enforce commit message rules

Add a shared validator, local commit-msg hook, and CI check so
repository commit messages follow the documented format.
```

```text
chore: bump tossinvest sdk

Pin tossinvest-openapi to the v1.0.2 release tag.

Align read-only MCP tool schemas with SDK enums and defaults.
```
