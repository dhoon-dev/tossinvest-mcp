from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts" / "validate_release_tag.py"))
read_versions: Callable[[], dict[str, str]] = MODULE["_read_versions"]
version_from_tag: Callable[[str], str | None] = MODULE["_version_from_tag"]


def test_version_from_tag_accepts_v_prefixed_tags() -> None:
    assert version_from_tag("v1.2.3") == "1.2.3"


def test_version_from_tag_rejects_non_release_tags() -> None:
    assert version_from_tag("1.2.3") is None
    assert version_from_tag("v") is None


def test_release_version_declarations_match() -> None:
    versions = read_versions()

    assert set(versions) == {
        "pyproject.toml [project.version]",
        "uv.lock package tossinvest-mcp",
        "src/tossinvest_mcp/_version.py __version__",
        "docs/conf.py release",
    }
    assert len(set(versions.values())) == 1
