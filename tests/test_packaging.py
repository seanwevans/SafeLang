"""Guards on the packaging metadata, so a release cannot ship a broken wheel."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import safelang

tomllib = pytest.importorskip("tomllib", reason="needs Python 3.11+ to read TOML")

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
PROJECT = PYPROJECT["project"]

# PEP 440, restricted to the release/pre-release forms this project uses.
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.post\d+)?$")


def test_version_is_pep440():
    assert _VERSION_RE.fullmatch(safelang.__version__), safelang.__version__


def test_version_is_read_from_the_package():
    assert PROJECT["dynamic"] == ["version"]
    dynamic = PYPROJECT["tool"]["setuptools"]["dynamic"]
    assert dynamic["version"] == {"attr": "safelang.__version__"}


def test_cli_reports_the_same_version():
    result = subprocess.run(
        [sys.executable, "-m", "safelang", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"safelang {safelang.__version__}"


def test_requires_python_matches_the_syntax_actually_used():
    """parser.py uses PEP 604 unions in evaluated annotations, so 3.10 is the floor."""

    assert PROJECT["requires-python"] == ">=3.10"
    source = (ROOT / "safelang" / "parser.py").read_text()
    assert "str | None" in source
    assert "from __future__ import annotations" not in source


def test_metadata_is_filled_in():
    assert PROJECT["name"] == "safelang-verifier"
    assert PROJECT["license"] == "MIT"
    assert PROJECT["license-files"] == ["LICENSE"]
    assert PROJECT["authors"]
    assert PROJECT["keywords"]
    assert PROJECT["readme"] == "README.md"
    assert PROJECT["description"]


def test_project_urls_point_at_the_repository():
    urls = PROJECT["urls"]
    assert urls["Repository"].endswith("/SafeLang")
    assert all(url.startswith("https://") for url in urls.values())


def test_classifiers_cover_every_supported_python():
    classifiers = PROJECT["classifiers"]
    for minor in (10, 11, 12, 13):
        assert f"Programming Language :: Python :: 3.{minor}" in classifiers
    # PEP 639: the license expression replaces the deprecated classifier, and
    # setuptools rejects a build that declares both.
    assert not any(c.startswith("License ::") for c in classifiers)


def test_console_script_points_at_main():
    assert PROJECT["scripts"] == {"safelang": "safelang.__main__:main"}


def test_only_the_library_package_is_shipped():
    assert PYPROJECT["tool"]["setuptools"]["packages"] == ["safelang"]


def test_javascript_runtime_is_declared_as_package_data():
    package_data = PYPROJECT["tool"]["setuptools"]["package-data"]
    assert "runtime.js" in package_data["safelang"]
    assert (ROOT / "safelang" / "runtime.js").is_file()


def test_manifest_ships_the_c_runtime_and_the_specs():
    manifest = (ROOT / "MANIFEST.in").read_text()
    for entry in ("SPEC.md", "GRAMMAR.md", "example.slang", "runtime-c"):
        assert entry in manifest


def test_release_workflow_uses_trusted_publishing():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert "password" not in workflow
    assert "PYPI_API_TOKEN" not in workflow


def test_release_workflow_refuses_a_mismatched_tag():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "safelang.__version__" in workflow
    assert "does not match" in workflow
