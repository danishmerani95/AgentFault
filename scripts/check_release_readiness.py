"""Check release metadata before publishing a stable version of AgentFault."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys
import tomllib


def check_release_readiness(
    root: Path,
    *,
    require_stable: bool = False,
) -> list[str]:
    """Return release-gate failures; an empty list means the gate passed."""
    project_file = root / "pyproject.toml"
    try:
        with project_file.open("rb") as file:
            project_data = tomllib.load(file)["project"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        return [f"could not read project metadata: {error}"]

    version = project_data.get("version")
    if not isinstance(version, str):
        return ["project.version must be a string"]

    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", version)
    if match is None:
        return [f"project.version {version!r} is not a valid numeric semantic version"]

    major = int(match.group(1))
    is_prerelease = bool(match.group(4))
    is_stable_version = major >= 1 and not is_prerelease

    if not is_stable_version:
        if require_stable:
            return [
                f"version {version} is not a stable 1.0.0-or-newer release target"
            ]
        return []

    failures: list[str] = []
    classifiers = project_data.get("classifiers", [])
    stable_classifier = "Development Status :: 5 - Production/Stable"
    if stable_classifier not in classifiers:
        failures.append(
            f"pyproject.toml must include classifier {stable_classifier!r}"
        )
    if any(
        classifier in {
            "Development Status :: 3 - Alpha",
            "Development Status :: 4 - Beta",
        }
        for classifier in classifiers
    ):
        failures.append("stable releases must not retain Alpha or Beta classifiers")

    changelog_path = root / "CHANGELOG.md"
    try:
        changelog = changelog_path.read_text(encoding="utf-8")
    except OSError as error:
        failures.append(f"could not read CHANGELOG.md: {error}")
        changelog = ""

    release_heading = re.search(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
        changelog,
        flags=re.MULTILINE,
    )
    if release_heading is None:
        failures.append(
            f"CHANGELOG.md must contain a dated heading "
            f"'## [{version}] - YYYY-MM-DD'"
        )
    else:
        try:
            date.fromisoformat(release_heading.group(1))
        except ValueError:
            failures.append(
                f"CHANGELOG.md release date {release_heading.group(1)!r} is invalid"
            )

    readme_path = root / "README.md"
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError as error:
        failures.append(f"could not read README.md: {error}")
        readme = ""
    if re.search(r"project status:\s*alpha", readme, flags=re.IGNORECASE):
        failures.append("README.md still describes the project status as alpha")
    if re.search(r"\bAPIs may change\b", readme, flags=re.IGNORECASE):
        failures.append(
            "README.md still states that APIs may change without a stable-release qualifier"
        )

    for relative_path in ("docs/api-stability.md", "docs/releasing.md"):
        if not (root / relative_path).is_file():
            failures.append(f"required release documentation is missing: {relative_path}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-stable",
        action="store_true",
        help="fail unless project metadata targets a stable 1.0.0-or-newer version",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (used by tests; defaults to this script's repository)",
    )
    args = parser.parse_args()

    failures = check_release_readiness(args.root, require_stable=args.require_stable)
    version = "unknown"
    try:
        with (args.root / "pyproject.toml").open("rb") as file:
            version = tomllib.load(file)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        pass

    if not args.require_stable and failures == []:
        with (args.root / "pyproject.toml").open("rb") as file:
            project_version = tomllib.load(file)["project"]["version"]
        if re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", project_version):
            match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", project_version)
            assert match is not None
            if int(match.group(1)) < 1 or match.group(4):
                print(
                    f"Stable-release gate not applicable to pre-stable version "
                    f"{project_version}; tag/version matching and normal CI still apply."
                )
                return 0

    if failures:
        print(f"Stable-release gate FAILED for agentfault {version}:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    if args.require_stable:
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", version)
        if match is None or int(match.group(1)) < 1 or match.group(4):
            print(
                f"Stable-release gate FAILED: version {version} is not stable.",
                file=sys.stderr,
            )
            return 1

    print(f"Stable-release gate passed for agentfault {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
