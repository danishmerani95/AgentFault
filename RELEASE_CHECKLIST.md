# First Release Checklist

Use this checklist before publishing the first public Agent Fault release. Do not publish automatically from this checklist; repository visibility, package identity, version, and destination are deliberate release decisions.

## Project identity and license

- [ ] Confirm the repository is intended to be public before publishing.
- [x] Display-name decision: use **Agent Fault**. A separate product named AgentFault exists at [agentfault.com](https://agentfault.com/); the similar name remains a potential source of confusion, so the public description should clearly state that this project is an open-source AI-agent reliability testing library.
- [ ] Verify the PyPI distribution name `agentfault` directly against PyPI before upload; availability has not yet been conclusively established.
- [x] License decision confirmed: use the MIT License. Keep the `LICENSE` file and package metadata consistent with MIT.
- [ ] Review ownership and copyright information in `LICENSE`.
- [ ] Review the README, contributor guide, changelog, and example scenario commands for accuracy.

## Package readiness

- [x] Confirm the version in `pyproject.toml` (`0.1.0`) is the intended first alpha release version.
- [x] Confirm `uv.lock` is in sync with the project configuration (the current main-branch CI uses `uv sync --locked` successfully).
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
