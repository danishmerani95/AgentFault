# Results and Troubleshooting

A test result is useful when it tells you both whether an invariant held and what the agent actually did. Inspect the assertion messages and recorded trajectory before changing prompts or code.

## Scenario results

A call to `ScenarioRunner(tool_registry).run(scenario)` returns a result with:

- `passed`: true only when there is no terminal runner error and all configured assertions pass.
- `assertions`: the result from each assertion, with a boolean and explanatory message.
- `trajectory`: the sequence of tool calls and the associated observations/errors.
- `error`: a terminal runner error when the step limit is reached.

A simple report:

```python
result = ScenarioRunner(tool_registry).run(scenario)

print("passed:", result.passed)
print("terminal error:", result.error)
for item in result.assertions:
    print(("PASS" if item.passed else "FAIL"), item.message)

for step in result.trajectory:
    print(
        step.tool_call.name,
        "succeeded=", step.succeeded,
        "observation=", step.observation,
        "error=", step.error,
    )
```

Trajectory contents can include application data returned by tools. Avoid printing or sharing production credentials, customer data, private documents, or sensitive tool outputs in CI logs.

## Benchmark results

`BenchmarkRunner.run(...)` returns a benchmark result with counts and a `to_dict()` method. The JSON-safe output lists each case's status, error string, assertion messages, and observed tool-call names.

- **`passed`**: the scenario's assertions passed without a terminal runner error.
- **`failed`**: the scenario completed, but one or more behavioral assertions did not pass.
- **`error`**: setup or execution raised an error, or a case ended with a terminal scenario error.

When any case status is `error`, the aggregate benchmark is incomplete and `score` is `None`. Fix or explain execution errors before comparing pass percentages. See [Benchmarks](benchmarks.md).

## Common problems

### The perturbation never applied

Check that the trigger's name exactly matches the registered tool-call name. `AfterTool` runs only after a matching tool succeeds; it is not a general timer or an “after agent thought” trigger. For a failure to occur before execution, consider `BeforeTool` or a scheduled tool-failure perturbation with a specific matching tool name.

Also verify the environment object and target identifiers. The built-in `ChangePrice` and `ChangeInventory` expect an Agent Fault `CommerceEnvironment` with the referenced offer ID; they are not arbitrary object mutation helpers.

### The agent's calls are missing from the trajectory

For the generic runner, the agent must return a `ToolCall` and let Agent Fault execute it through the provided `ToolRegistry`. If the agent directly invokes the underlying function, uses its own framework executor, or calls an uninstrumented tool from another graph node, that work may bypass Agent Fault's hooks.

Use the matching framework integration when the framework owns the loop. Read [Integrations](integrations.md), particularly the limits of the current LangGraph integration.

### A tool failed, but the scenario did not stop

A registered tool exception is represented as a tool-error observation and recorded on the trajectory. The agent gets an opportunity to retry, recover, or stop. A failed tool call does not automatically mean the overall scenario failed; the assertions decide whether the resulting behavior was acceptable.

If your invariant is that a consequential action must never be attempted, inspect every trajectory step with a custom assertion. The built-in `ProhibitedActionAssertion` checks whether a named action **succeeded**, not whether it was attempted and then errored.

### The result has no numeric benchmark score

Look for cases with status `error` and inspect their error text. An exception in case construction, the agent factory, or model/provider invocation can invalidate a case. Correct the execution/configuration error before comparing behavioral scores.

### The scenario hits the step limit

The generic runner defaults to a maximum of 100 tool executions. A result with a terminal error indicating the maximum was reached means the agent did not return `None` in time. For a legitimate long workflow, pass a reasonable larger `max_steps`; for a loop, inspect the trajectory and fix the repeated decision pattern instead of increasing the limit without bound.

### An example cannot be imported after installation

The source distribution/install contains the `agentfault` package, not the repository's top-level `examples` package. Clone the repository and run the documented examples from the repository root. Provider and framework examples may also need optional dependencies and environment variables.

### A custom scenario behaves differently on each run

Check for hidden shared state, timestamps, random IDs, model variation, tool ordering, concurrency, and external service dependencies. Start with deterministic tools and a fresh environment. When evaluating an LLM agent, record the provider/model, prompts, configuration, package version, and relevant framework version with each run.

## Debugging sequence

1. Re-run the smallest scenario that reproduces the failure.
2. Confirm the trigger fired and the intended environment state changed.
3. Inspect the exact tool-call sequence and each observation.
4. Read the assertion message to identify the violated invariant.
5. Only then adjust the agent, tools, perturbation timing, or assertion.

The trajectory is evidence of what went through the configured execution path; it is not a complete trace of code that bypassed Agent Fault's hooks.

## Execution event timeline

Each `ScenarioResult` now includes `events`, an ordered list of `TraceEvent` values. Events cover scenario start/end, tool and model call start/completion, injected faults, and environment perturbations. Call-completion events include elapsed duration; model/tool events share a call ID when the framework provides one. Timestamps are UTC ISO-8601, and elapsed/duration fields use a monotonic clock.

Inspect the timeline directly:

```python
result = ScenarioRunner(tool_registry).run(scenario)
for event in result.events:
    print(
        event.sequence,
        event.timestamp,
        event.elapsed_ms,
        event.kind,
        event.phase,
        event.name,
        event.outcome,
        event.duration_ms,
    )
```

Benchmark `result.to_dict()` also includes each case's `events` list for JSON logs and report collection. Event details intentionally omit prompts, raw model responses, and tool arguments by default; add application-specific sanitized metadata in a separate layer if it is needed for diagnostics.
