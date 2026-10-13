# Changelog

Notable changes to Agent Fault are documented here.

This project is in alpha. Until the first release is tagged, changes are collected under `Unreleased`.

## [Unreleased]

### Added
- Scheduled tool and model API fault injection for transient failures, timeouts, latency, malformed/empty responses, and provider-like errors.
- Repeated benchmark evaluation with per-case pass rates, pass^k, score means, population standard deviations, and explicit incomplete/error handling.
- Native LangChain v1 middleware, sync/async LangGraph ToolNode interception, and an optional Anthropic Messages API agent adapter.
- Timestamped scenario event timelines with monotonic duration measurements, fault/perturbation evidence, and per-case JSON trace serialization.
- A versioned benchmark API with per-case results, assertion evidence, tool-call summaries, and scoring withheld for incomplete runs.
- The `buying-agent@1.0.0` benchmark suite for safe purchases under price and inventory changes.
- OpenAI and LangChain examples for the Benchmark API, plus a native LangGraph custom-scenario example.
- An optional LangChain integration workflow that checks adapter behavior without model API calls.
- CI validation for Python 3.12, 3.13, and 3.14, including a clean-wheel installation smoke test.

### Changed
- The README is organized around the two public use cases: reusable benchmarks and custom scenarios, with framework examples for OpenAI, LangChain, and LangGraph.
- The product's display name is written as **Agent Fault**; the Python import package and distribution identifier remain `agentfault`.
- The deterministic commerce reference agent rechecks the offer price and inventory after adding an item to the cart.

### Notes
- APIs are in alpha and may change before the first stable release.
- The built-in benchmark currently covers buying agents; other categories can use custom scenarios or add versioned suites.
- The first release version and date will be recorded when a release is actually published.
