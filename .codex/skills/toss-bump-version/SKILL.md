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
docs/conf.py release
uv.lock package tossinvest-mcp-remote version
```

4. Edit source declarations first, then update the lockfile with:

```bash
uv lock
```

5. Validate the version declarations against the intended tag:

```bash
uv run --locked python scripts/validate_release_tag.py vX.Y.Z
```

6. Run the project quality gate before handing off broad version bumps:

```bash
uv sync --locked --all-extras --group docs
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest -m "not live"
uv run --locked --group docs sphinx-build -W -b html docs docs/_build/html
uv build
```

7. Report the changed version, changed files, and validation commands.

## Commit Guidance

If the user asks to commit the version bump, use `$toss-commit-changes`.
Recommended message shape:

```text
chore: bump version to X.Y.Z

Update package, lockfile, runtime, and documentation version declarations
for the X.Y.Z release.
```
