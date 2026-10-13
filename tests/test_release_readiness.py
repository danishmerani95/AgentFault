"""Tests for the stable release metadata gate."""

from pathlib import Path

from scripts.check_release_readiness import check_release_readiness


def _write_release_fixture(
    root: Path,
    *,
    version: str = "1.0.0",
    classifier: str = "Development Status :: 5 - Production/Stable",
    changelog: str = "## [1.0.0] - 2026-10-13\n\nFirst stable release.\n",
    readme: str = "# Agent Fault\n\n**Project status: stable.**\n",
) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\n"
        f'version = "{version}"\n'
        f'classifiers = ["{classifier}"]\n',
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "docs" / "api-stability.md").write_text(
        "Documented public API and breaking changes.\n",
        encoding="utf-8",
    )
    (root / "docs" / "releasing.md").write_text(
        "Release checklist.\n",
        encoding="utf-8",
    )


def test_valid_stable_release_metadata_passes(tmp_path: Path) -> None:
    _write_release_fixture(tmp_path)

    assert check_release_readiness(tmp_path, require_stable=True) == []


def test_alpha_release_skips_stable_gate_unless_required(tmp_path: Path) -> None:
    _write_release_fixture(
        tmp_path,
        version="0.1.0",
        classifier="Development Status :: 3 - Alpha",
        changelog="## [Unreleased]\n\nWork in progress.\n",
        readme="# Agent Fault\n\n**Project status: alpha.**\n",
    )

    assert check_release_readiness(tmp_path) == []
    assert "not a stable" in check_release_readiness(
        tmp_path, require_stable=True
    )[0]


def test_stable_release_fails_for_stale_metadata(tmp_path: Path) -> None:
    _write_release_fixture(
        tmp_path,
        classifier="Development Status :: 3 - Alpha",
        changelog="## [Unreleased]\n\nNo dated release notes yet.\n",
        readme="# Agent Fault\n\n**Project status: alpha.** APIs may change.\n",
    )

    failures = check_release_readiness(tmp_path, require_stable=True)

    assert any("Production/Stable" in failure for failure in failures)
    assert any("Alpha or Beta classifiers" in failure for failure in failures)
    assert any("dated heading" in failure for failure in failures)
    assert any("still describes the project status as alpha" in failure for failure in failures)
    assert any("APIs may change" in failure for failure in failures)


def test_stable_release_rejects_invalid_release_date(tmp_path: Path) -> None:
    _write_release_fixture(
        tmp_path,
        changelog="## [1.0.0] - 2026-99-42\n\nFirst stable release.\n",
    )

    failures = check_release_readiness(tmp_path, require_stable=True)

    assert any("invalid" in failure for failure in failures)


def test_stable_release_rejects_prerelease_version(tmp_path: Path) -> None:
    _write_release_fixture(
        tmp_path,
        version="1.0.0rc1",
        changelog="## [1.0.0rc1] - 2026-10-13\n\nCandidate.\n",
    )

    failures = check_release_readiness(tmp_path, require_stable=True)

    assert failures == [
        "version 1.0.0rc1 is not a stable 1.0.0-or-newer release target"
    ]
