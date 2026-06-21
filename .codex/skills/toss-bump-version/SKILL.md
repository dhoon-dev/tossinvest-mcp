---
name: toss-bump-version
description: Repository-specific workflow for bumping the tossinvest-mcp-remote release version. Use when the user asks to bump, release, prepare, or validate this repo's package version, including patch/minor/major changes and release tag checks.
---

# Toss Bump Version

## Workflow

1. Confirm the target version if the user did not specify it. Prefer a patch
   bump for tooling-only changes unless the user asks otherwise.

2. Check the tree before edits:

```bash
git status --short --branch
```

3. Update exactly these project version declarations:

```text
pyproject.toml [project].version
src/tossinvest_mcp_remote/_version.py __version__
uv.lock package tossinvest-mcp-remote version
```

4. Edit source declarations first, then update the lockfile with:

```bash
uv lock
```

5. Validate the version declarations by checking the package version surfaces:

```bash
uv run --locked tossinvest-mcp-remote version
uv run --locked python -c "import tossinvest_mcp_remote; print(tossinvest_mcp_remote.__version__)"
```

6. Run the project quality gate before handing off broad version bumps:

```bash
uv sync --locked --all-extras
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest
```

7. Report the changed version, changed files, and validation commands.

## Commit Guidance

If the user asks to commit the version bump, use `$toss-commit-changes`.
Recommended message shape:

```text
chore: bump version to X.Y.Z

Update package, lockfile, and runtime version declarations for the
X.Y.Z release.
```
