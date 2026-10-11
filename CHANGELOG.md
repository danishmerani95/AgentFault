# Changelog

Notable changes to AgentFault are documented here.

This project is in alpha. Until the first release is tagged, changes are collected under `Unreleased`.

## [Unreleased]

### Added
- A versioned benchmark API with per-case results, assertion evidence, tool-call summaries, and scoring withheld for incomplete runs.
- The `buying-agent@1.0.0` benchmark suite for safe purchases under price and inventory changes.
- An OpenAI benchmark example and a native LangGraph custom-scenario example.
- CI validation for Python 3.12, 3.13, and 3.14, including a clean-wheel installation smoke test.

### Changed
- The README is organized around the two public use cases: reusable benchmarks and custom scenarios.
- The deterministic commerce reference agent rechecks the offer price and inventory after adding an item to the cart.

### Notes
- APIs are in alpha and may change before the first stable release.
- The built-in benchmark currently covers buying agents; other categories can use custom scenarios or add versioned suites.
- The first release version and date will be recorded when a release is actually published.
