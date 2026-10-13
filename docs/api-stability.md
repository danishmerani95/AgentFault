# API compatibility and versioning policy

Agent Fault is in alpha until its first stable release. Before the first `1.0.0` release, public APIs may change when needed; release notes must describe material changes and migration steps.

Once `1.0.0` is released, the following policy applies.

## What is public

The public API consists of documented symbols and the supported surfaces listed below:

- Top-level package exports from `agentfault` and documented APIs in `agentfault.testing` and `agentfault.benchmarks`.
- The `Agent` contract, scenario/tool/fault/trigger/assertion protocols, result objects and their documented fields.
- Stable CLI commands and arguments.
- Versioned benchmark suite identifiers, case identifiers, and documented result/JSON fields.
- The supported integration adapters and their documented sync/async execution boundaries.

Undocumented internal modules, private names beginning with an underscore, and implementation details not included in the documentation are not covered by compatibility promises.

## Semantic versioning

- **Patch** (`1.0.x`): backward-compatible bug fixes, documentation corrections, and low-risk internal improvements.
- **Minor** (`1.x.0`): backward-compatible functionality, new optional integrations, new fault types, assertions, triggers, and benchmark cases/suites.
- **Major** (`x.0.0`): intentional breaking changes to public APIs, supported execution semantics, or documented result schemas.

A new benchmark case should receive a stable unique case ID within its suite. Changes to the meaning of an existing case or the fields/semantics of a published result should be treated as a compatibility change, not silently redefined.

## Deprecation

After stable release, a public API slated for removal should first be documented as deprecated, include a replacement where possible, and remain available for at least one minor release and six months, whichever is longer. Security, legal, or severe correctness concerns may require a shorter window; such exceptions must be explained in release notes.

## Integrations

A framework integration only claims the execution paths and fault boundaries covered by its tests and documentation. In particular, tool execution is observable only when it passes through an AgentFault executor or configured native framework hook. Async, parallel, streaming, and provider-specific behavior must be called out separately when unsupported or only partially supported.

Optional provider/framework SDKs must remain optional unless the core product contract changes deliberately and the dependency impact is explained.

## Result and trace compatibility

Scenario and benchmark results may gain additive fields in a minor release. Removing or changing the type or meaning of a documented field is a breaking change. Trace event names, outcomes, and documented metadata are treated as public when described in API documentation.

## Changes before 1.0.0

Before the stable release, maintainers may revise these guarantees based on release-candidate testing. The stable-release checklist must be completed before changing package metadata to `1.0.0`; the version number and production/stable classifier must never be used as a substitute for passing the release gates.
