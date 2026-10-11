# Scenario Pack Contract

**Status:** Product/specification draft. This document defines the intended authoring contract; it does not claim that a public Scenario Pack API or serialized pack loader is implemented.

## Purpose

A scenario pack is a versioned, reusable collection of behavioral tests for a class of agent work. It lets engineers test different agents against the same failure conditions while keeping the agent's framework and model separate from the job being tested.

AgentFault's differentiator is the controlled change to the world around an agent and the evidence of what the agent does next—not merely the quality of its final text.

## Concepts

- **Category:** the job the agent performs, such as buying, search/research, or customer support.
- **Pack:** metadata, compatibility requirements, default run policy, and one or more scenarios, released under an immutable version.
- **Scenario:** one test with a defined initial world, agent task, intervention (if any), behavioral contract, and evaluation rules.
- **Integration/adapter:** the mechanism for routing proposed tool calls through AgentFault. Frameworks such as LangGraph are not scenario categories.
- **Run:** one execution of one pack version against one agent and isolated environment.
- **Custom extension:** user-authored scenarios or overrides executed alongside a pack, but reported separately from any standardized benchmark result.

## Pack metadata contract

Every pack should define:

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | Stable, machine-readable identifier, e.g. `buying-agent`. |
| `version` | Yes | Immutable pack version. Any change to scenarios, initial state, perturbations, assertions, or scoring rules requires a new version. |
| `title`, `description` | Yes | Human-readable name and what the pack tests. |
| `category` | Yes | Agent job/role, not framework or model vendor. |
| `intended_capabilities` | Yes | Behaviors covered and important non-goals. |
| `required_tools` / `tool_contracts` | Yes | Semantic capabilities and expected inputs/outputs, including side effects. Names may be mapped by an adapter. |
| `environment` | Yes | Initial-state factory or fixture contract, reset guarantees, and isolation requirements. |
| `scenarios` | Yes | Stable list of scenario IDs and their versioned definitions. |
| `evaluation_policy` | Yes | Assertion semantics, status meanings, aggregation and coverage reporting. |
| `compatibility_profiles` | For benchmarks | Predefined capability profiles that determine eligibility before execution. |
| `safety` | Yes | Side effects permitted, sandbox assumptions, and prohibited connections. |

Pack identity must not depend on a display title or repository path. Scenario IDs remain stable across edits when the behavioral contract is genuinely the same; materially different expected behavior gets a new scenario ID.

## Scenario contract

Each scenario definition should express the following in human-readable and eventually machine-readable form:

1. **Identity:** stable ID, title, intent, tags, and severity/importance.
2. **Agent task:** the user-facing goal and constraints provided to the agent. Do not include the expected solution in the task text.
3. **Preconditions and initial state:** relevant products/accounts/permissions, tool data, budgets, and starting facts. State must be created fresh for each run.
4. **Required capabilities:** semantic tools or operations the agent must be able to perform.
5. **Intervention:** optional perturbation, trigger point, changed state or injected failure, and the evidence proving it actually fired. The trigger must be observable and deterministic where possible.
6. **Behavioral contract:** required outcomes and prohibited actions, especially consequential actions such as purchases, refunds, deletions, and permission changes.
7. **Assertions:** individually named checks with pass/fail criteria and the evidence they inspect. Assertions should prefer world state and tool/action trajectory over a final-answer string.
8. **Applicability:** the capability or declared environment condition that makes a scenario applicable. Applicability must be decidable before the agent is run whenever possible.
9. **Isolation and limits:** reset guarantee, maximum steps, timeout, and any allowed retries or repeated trials.
10. **Known limitations:** assumptions or behaviors that the scenario does not prove.

A scenario must not silently pass because a perturbation failed to trigger, an expected tool was unavailable, or the runner crashed. Those cases are execution errors or incomplete runs, not successful agent behavior.

## Run result contract

Each scenario result should include:

- pack ID/version and scenario ID;
- run ID and agent/integration identifiers supplied by the user;
- status and individual assertion outcomes;
- intervention configuration and whether it actually fired;
- relevant tool-call trajectory (names, sanitized arguments/results, success/error);
- relevant before/after world-state evidence;
- duration, step count, and execution error details when applicable.

Do not collect hidden chain-of-thought as evidence. Explain failures through observable actions, tool inputs/outputs, state changes, and failed assertions. Redact credentials and user-configured sensitive fields before logs are persisted.

### Scenario statuses

| Status | Meaning | Counts as pass? |
|---|---|---|
| `passed` | All required assertions passed and the run was valid. | Yes |
| `failed` | The run was valid but one or more behavioral assertions failed. | No |
| `error` | The scenario could not be evaluated validly, e.g. adapter crash or perturbation did not fire. | No; result is invalid/incomplete |
| `not_run` | The scenario was intentionally not executed. | No |
| `not_applicable` | A documented capability/precondition is outside the agent's declared scope. | No; report separately |

A user can mark a scenario not applicable in flexible scenario testing, but must provide a reason. Never relabel a failure as not applicable after seeing the outcome without preserving the audit trail. Always report counts and coverage, not just a pass percentage.

## Two product surfaces, shared execution engine

### Scenario Testing API — flexible

Intended use: diagnose a particular agent.

- Select a pack and version.
- Override supported initial-state values or intervention parameters.
- Add custom scenarios and assertions.
- Mark scenarios as not applicable with a reason.
- Run repeatedly to reproduce a failure.

A customized run is identified as customized. Results from different custom configurations are not directly comparable by default. Baseline pack results and custom extensions must be separated in the report.

### Benchmark API — standardized

Intended use: compare agents under the same test conditions.

- Select an immutable benchmark ID/version and a predefined compatibility profile.
- Provide an agent integration and its declared tool mapping.
- Permit only explicitly allowed configuration that does not alter scenario semantics or scoring.
- Execute the official suite in a controlled, resettable environment.
- Produce the official score, coverage, per-scenario results, and evidence.

Custom scenarios can run as a separate extension but never change the official score. Any change to the official suite, fixtures, intervention timing, assertions, or scoring rules requires a new benchmark version. Do not compare headline scores across different benchmark versions or materially different compatibility profiles as if they were equivalent.

## Benchmark scoring and comparability

For the first benchmark, use equal weight per eligible scenario and report:
- **Score:** passed official scenarios divided by eligible official scenarios, only when all eligible scenarios completed validly.
- **Coverage:** eligible official scenarios divided by the full suite, with not-applicable reasons shown.
- **Breakdown:** passed, failed, error, not run, and not applicable counts, plus each scenario's evidence.

Eligibility should be derived from a declared, predefined compatibility profile before a run starts. An execution error makes the benchmark incomplete; it must not be converted into a failure of the agent or silently excluded from the denominator. Post-run exclusions invalidate the headline score until rerun or reviewed.

A score is comparable only when benchmark version, compatibility profile, tool semantics, environment fixture, intervention schedule, assertion rules, and run policy match. Record model/provider/version and relevant agent configuration where the user can supply them. For non-deterministic agents, disclose repeat count and aggregation method; never imply one run measures universal reliability.

## Safety and operational requirements

- Default to synthetic fixtures, fake services, and isolated sandboxes.
- Never run a benchmark against production systems or allow real purchases/refunds by default.
- Require explicit opt-in for any adapter that can touch external systems.
- Bound execution steps, wall-clock time, and repeated trials.
- Make resets reliable; detect and report a failed reset.
- Sanitize secrets and sensitive tool data in persisted evidence.
- Keep pack and benchmark versions immutable after publication.

## Acceptance criteria for the first implementation

The first implementation of this contract is complete when:

1. A pack has stable identity/version metadata and can describe multiple scenarios.
2. Each scenario defines state, task, required capabilities, intervention, assertions, applicability, and limits.
3. The runner distinguishes behavioral failure from execution error.
4. Reports include trajectory/evidence and scenario coverage.
5. Custom scenarios and exclusions never alter the official benchmark score.
6. Benchmark results identify their immutable suite version and compatibility profile.
7. Tests use isolated synthetic state and cannot accidentally invoke live purchasing operations.
