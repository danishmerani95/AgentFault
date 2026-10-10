# Changelog

Notable changes to AgentFault are documented here.

This project is in alpha. Until the first release is tagged, changes are collected under `Unreleased`.

## [Unreleased]

### Added
- Stateful scenarios with perturbations that change environment state before or after tool calls.
- Controlled tool-failure injection with structured error feedback and trajectory evidence.
- Assertions for budget limits and prohibited consequential actions.
- A CLI for running scenario factories and a pytest plugin using the same scenario runner.
- A generic OpenAI tool-calling adapter alongside the commerce example integration.
- Example scenarios for state changes, transient tool recovery, and unsafe purchases.
- CI validation for Python 3.12, 3.13, and 3.14, including a clean-wheel installation smoke test.

### Notes
- The API is in alpha and may change before the first stable release.
- The first release version and date will be recorded when a release is actually published.
