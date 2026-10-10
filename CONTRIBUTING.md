# Contributing to AgentFault

Thanks for contributing. AgentFault is an alpha project focused on testing how tool-using agents behave when the environment changes or tools fail.

## Development setup

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

From the repository root:

```bash
uv sync --extra dev
```

## Checks before opening a pull request

Run the test suite, lint, type-check, and package build:

```bash
uv run pytest
uv run ruff check .
uv run mypy src/agentfault
uv build
```

GitHub Actions runs the same checks on Python 3.12, 3.13, and 3.14, then installs the built wheel in a clean environment and smoke-tests the CLI and pytest integration.

## Change guidelines

- Keep agent execution generic. Domain-specific behavior belongs in environments, tools, scenarios, perturbations, or assertions.
- Prefer small, runnable examples that demonstrate one behavioral contract.
- When changing scenario behavior, add a test that covers the expected outcome and relevant trajectory evidence.
- Do not make an intentionally failing example appear to pass. Document expected failure behavior explicitly.
- Avoid adding runtime dependencies unless they are needed for a clear user-facing capability.

## Pull requests

Use a focused change with a Conventional Commit-style title, explain the motivation and behavioral impact, and note the checks you ran. Do not claim checks passed unless you ran them or CI reports success.
