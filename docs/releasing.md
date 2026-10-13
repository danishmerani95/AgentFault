# Release checklist

This checklist covers alpha releases and the first stable `1.0.0` release. A release is not ready solely because one feature branch or pull request is green; the complete integration must be tested after all dependent changes have been combined.

## Before the first stable release

- [ ] Resolve the stable-readiness items in [issue #22](https://github.com/danishmerani95/AgentFault/issues/22).
- [ ] Merge and integrate the planned feature PRs, including fault injection/repeated evaluation, the benchmark packs, framework examples, native LangChain middleware, event timelines, async LangGraph hooks, and the Anthropic adapter.
- [ ] Run the combined test suite on Python 3.12, 3.13, and 3.14, with optional LangChain/LangGraph integration dependencies installed in the integration job.
- [ ] Verify `ruff`, strict `mypy`, wheel/sdist build, distribution metadata, clean-wheel installation, CLI smoke test, and pytest plugin smoke test.
- [ ] Verify tool/model fault lifecycle tests, state perturbations, and traces for both success and error paths. Ensure expected failures are not counted as passes.
- [ ] Check benchmark aggregation against hand-calculated fixtures, including pass rate, pass^k, mean, population standard deviation, and incomplete/error runs.
- [ ] Test every built-in suite with safe and intentionally unsafe reference agents. Clearly label synthetic suites; do not imply that they reproduce external benchmark datasets.
- [ ] Exercise framework adapters against their documented supported sync/async paths without requiring live provider credentials in CI. Confirm unsupported execution paths fail clearly rather than silently bypassing injection.
- [ ] Review public exports, API stability policy, compatibility boundaries, README status, docs, and examples.
- [ ] Add dated `[1.0.0]` release notes to `CHANGELOG.md`, including breaking changes, migrations, and notable limitations.
- [ ] Only after the checklist is complete, set `pyproject.toml` to `1.0.0`, change the classifier to `Development Status :: 5 - Production/Stable`, and update the README project status.
- [ ] Confirm the stable release gate passes against the exact commit that will be tagged.

## Tagging and publishing

1. Confirm the target commit is on `main` and all required CI checks are green on that exact commit.
2. Review `CHANGELOG.md`, metadata, and the tag/version match one last time.
3. Create the version tag (for example, `v1.0.0`) only after the stable-release gate passes.
4. Wait for the release workflow to finish its test matrix, build, metadata validation, and clean artifact upload.
5. Verify the published PyPI version and downloaded wheel/sdist. Do not treat a successful upload job as proof that the package's usage examples work.
6. Create the GitHub release with the matching changelog section and link to migration/compatibility documentation.
7. Run a clean installation from PyPI and the key offline example once more.

## Subsequent releases

For post-1.0 releases, follow the semantic-versioning and deprecation rules in [API stability](api-stability.md). Every release still needs the test matrix, lint, type check, distribution build, metadata validation, and clean installation smoke test. Keep release notes versioned and dated.
