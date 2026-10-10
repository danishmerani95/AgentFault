# First Release Checklist

Use this checklist before publishing the first public AgentFault release. Do not publish automatically from this checklist; the repository visibility, license, version, and package destination are deliberate release decisions.

## Project and license

- [ ] Confirm the repository is intended to be public before publishing.
- [ ] Explicitly confirm the chosen license. `LICENSE` currently contains the MIT License; keep the package metadata consistent with it unless the project owner chooses a different license.
- [ ] Review ownership and copyright information in `LICENSE`.
- [ ] Review the README, contributor guide, changelog, and example scenario commands for accuracy.

## Package readiness

- [ ] Confirm the distribution name `agentfault` is available and the intended PyPI project does not conflict with an existing project.
- [ ] Confirm the version in `pyproject.toml` (currently `0.1.0`) is the version intended for release.
- [ ] Confirm `uv.lock` is in sync with the project configuration.
- [ ] Run CI on the exact commit intended for release and require all checks to pass.
- [ ] Build the source distribution and wheel with `uv build`.
- [ ] Inspect the distributions and metadata before upload; test installing the wheel in a clean environment.
- [ ] Verify the CLI entry point and pytest plugin work from the installed distribution.

## Publish and announce

- [ ] Decide on and configure the trusted publishing or PyPI credentials workflow.
- [ ] Publish only after the above checks and owner approval.
- [ ] Create a version tag (for example, `v0.1.0`) that matches the released package.
- [ ] Create a GitHub release with notes drawn from `CHANGELOG.md`.
- [ ] Verify the published package can be installed into a fresh environment and the documented quick start works.
- [ ] Announce the release with the repository link and clear alpha-status expectations.
