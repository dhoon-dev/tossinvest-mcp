from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that a release tag matches project version declarations."
    )
    parser.add_argument("tag", help="Release tag, for example v1.0.0.")
    args = parser.parse_args()

    tag_version = _version_from_tag(args.tag)
    if tag_version is None:
        print("Release tags must start with 'v', for example v1.0.0.", file=sys.stderr)
        return 1

    versions = _read_versions()
    mismatches = {source: version for source, version in versions.items() if version != tag_version}
    if mismatches:
        print(
            f"Release tag {args.tag!r} resolves to {tag_version!r}, "
            "but version declarations do not match:",
            file=sys.stderr,
        )
        for source, version in versions.items():
            marker = "==" if version == tag_version else "!="
            print(f"- {source}: {version!r} {marker} {tag_version!r}", file=sys.stderr)
        return 1

    print(f"Release tag {args.tag} matches version {tag_version}.")
    return 0


def _version_from_tag(tag: str) -> str | None:
    if not tag.startswith("v"):
        return None
    version = tag.removeprefix("v")
    return version or None


def _read_versions() -> dict[str, str]:
    return {
        "pyproject.toml [project.version]": _read_project_version(),
        "uv.lock package tossinvest-mcp-remote": _read_lock_version(),
        "src/tossinvest_mcp_remote/_version.py __version__": _read_literal_assignment(
            ROOT / "src" / "tossinvest_mcp_remote" / "_version.py", "__version__"
        ),
        "docs/conf.py release": _read_literal_assignment(ROOT / "docs" / "conf.py", "release"),
    }


def _read_project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str):
        msg = "Missing string [project].version in pyproject.toml."
        raise TypeError(msg)
    return version


def _read_lock_version() -> str:
    with (ROOT / "uv.lock").open("rb") as handle:
        lockfile = tomllib.load(handle)
    packages = lockfile.get("package", [])
    if not isinstance(packages, list):
        msg = "Missing package list in uv.lock."
        raise TypeError(msg)
    for package in packages:
        if not isinstance(package, dict) or package.get("name") != "tossinvest-mcp-remote":
            continue
        version = package.get("version")
        if isinstance(version, str):
            return version
        msg = "Missing string version for tossinvest-mcp-remote in uv.lock."
        raise TypeError(msg)
    msg = "Missing tossinvest-mcp-remote package in uv.lock."
    raise ValueError(msg)


def _read_literal_assignment(path: Path, name: str) -> str:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in module.body:
        value = _assignment_value(statement, name)
        if value is not None:
            return value
    msg = f"Missing string assignment {name!r} in {path.relative_to(ROOT)}."
    raise ValueError(msg)


def _assignment_value(statement: ast.stmt, name: str) -> str | None:
    if isinstance(statement, ast.Assign):
        targets = statement.targets
        value = statement.value
    elif isinstance(statement, ast.AnnAssign):
        targets = [statement.target]
        value = statement.value
    else:
        return None

    if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
        return None
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value

    msg = f"Assignment {name!r} must be a string literal."
    raise TypeError(msg)


if __name__ == "__main__":
    raise SystemExit(main())
