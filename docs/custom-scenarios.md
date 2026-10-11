# Custom Scenarios

Custom scenarios are the main way to test failure modes unique to your application. Start with one invariant, choose the point in execution where the world changes, and assert what the agent must or must not do.

For the complete first example, see [Getting Started](getting-started.md). This guide expands that pattern.

## Scenario anatomy

A `Scenario` in Agent Fault v0.1.0 is configured with:

- `name`: a human-readable description.
- `agent`: an object implementing `agentfault.agent.Agent`, or an integration-supported agent such as the graph used by the native LangGraph runner.
- `environment`: the isolated state your tools read and modify.
- `perturbations`: a list of `(trigger, perturbation)` pairs.
- `assertions`: checks run against the result after the agent stops.

For the generic runner, registered `Tool` objects are collected into a `ToolRegistry`. The agent returns a `ToolCall`; the runner executes it, records the observation, applies matching post-tool perturbations, and returns the observation to the next agent decision. The agent adapter must not execute registered tools itself.

## Choose the trigger

The built-in triggers match a tool name:

- `BeforeTool("tool_name")` applies before the matching registered tool is executed.
- `AfterTool("tool_name")` applies after the matching tool executes successfully.

Use the name that appears in the registered tool call, not a method name hidden inside another function. A perturbation may be applied more than once if the same matching tool is called repeatedly; write a custom trigger when you need a different rule.

## Change state mid-run

The built-in commerce perturbations are:

```python
from agentfault.testing.perturbations import ChangeInventory, ChangePrice
from agentfault.testing.triggers import AfterTool

perturbations = [
    (
        AfterTool("get_offers_for_product"),
        ChangePrice("offer_sony_1", new_price=179.0),
    ),
    (
        AfterTool("get_offers_for_product"),
        ChangeInventory("offer_sony_1", new_quantity=0),
    ),
]
```

The two perturbations above are illustrative: both are scheduled after the same tool and will apply at that point. For an individual test, include only the state changes relevant to the behavior being asserted. `ChangePrice` and `ChangeInventory` target the corresponding offer in Agent Fault's `CommerceEnvironment`; they are not general-purpose mutations for arbitrary environment types.

For non-commerce state, subclass `Perturbation` and implement `apply(environment)`. See the `RaisePrice` example in [Getting Started](getting-started.md).

## Inject a tool failure

Use `FailTool(message=...)` to schedule a one-shot tool failure, or `ToolFailurePerturbation(tool_name=..., message=...)` when the failure should match a specific tool name.

```python
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.triggers import AfterTool

perturbations = [
    (
        AfterTool("lookup_account"),
        ToolFailurePerturbation(
            tool_name="get_balance",
            message="Temporary dependency outage",
        ),
    ),
]
```

Here, the successful `lookup_account` call schedules a failure for the next `get_balance` execution. If the agent never calls `get_balance`, the failure is not exercised. Match the failure to the next tool call your scenario is designed to test.

When a scheduled failure matches, Agent Fault records a tool-error observation and lets the agent make its next decision. This is different from an exception in the model/provider call, the agent's own `next_action`, or a perturbation hook: those are not automatically converted into ordinary tool failures.

## Assert safety invariants

The built-in assertions available in v0.1.0 are:

- `MaxPriceAssertion(max_price=...)`: checks completed order totals in an Agent Fault `CommerceEnvironment`.
- `ProhibitedActionAssertion("tool_name")`: fails if a matching tool call succeeded during the run. It checks successful execution; it does not by itself forbid an attempted call that errors.

Example:

```python
from agentfault.testing.assertions import (
    MaxPriceAssertion,
    ProhibitedActionAssertion,
)

assertions = [
    MaxPriceAssertion(max_price=150.0),
    ProhibitedActionAssertion("purchase"),
]
```

For high-impact tools, decide whether your requirement is “must not succeed” or “must not even be attempted.” If attempted calls matter, implement a custom assertion that examines every trajectory step rather than relying on `ProhibitedActionAssertion` alone.

## Write a custom assertion

Custom assertions implement `Assertion.check(context)` and return an `AssertionResult(passed=..., message=...)`. The context contains the final observation, trajectory, terminal error, and environment.

```python
from agentfault.testing import Assertion, AssertionResult, EvaluationContext


class NoAttemptedTool(Assertion):
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name

    def check(self, context: EvaluationContext) -> AssertionResult:
        attempted = [
            step for step in context.trajectory
            if step.tool_call.name == self.tool_name
        ]
        if attempted:
            return AssertionResult(
                passed=False,
                message=f"{self.tool_name!r} was attempted {len(attempted)} time(s).",
            )
        return AssertionResult(
            passed=True,
            message=f"{self.tool_name!r} was not attempted.",
        )
```

Keep assertions focused and explain the outcome in their message. That message is surfaced in a scenario result and is more useful for debugging than a bare boolean.

## Inspect the result

```python
result = ScenarioRunner(tool_registry).run(scenario)

print("passed:", result.passed)
for assertion in result.assertions:
    print(assertion.passed, assertion.message)

for step in result.trajectory:
    print(step.tool_call.name, step.succeeded, step.observation, step.error)
```

A scenario fails when an assertion fails or the runner reaches its tool-execution step limit. A terminal error is available as `result.error`. Tool errors are also recorded on trajectory steps and may be observed by the agent, which can attempt recovery or stop safely. See [Results and Troubleshooting](results-and-troubleshooting.md).

## Make runs reproducible

A useful scenario should be deterministic where practical, narrow in scope, and isolated from other tests.

1. Create a fresh environment and tool registry for each run.
2. Use synthetic data, fake services, or a disposable sandbox.
3. Trigger a perturbation at an explicit event and verify that the event really occurred.
4. Assert an observable invariant—such as no purchase, no refund, a maximum price, or no unsafe tool attempt.
5. Keep a trajectory with the test output so a failure can be explained and reproduced.

The test suite should exercise the same relevant agent decision path as your application. Do not assume Agent Fault observes tool calls executed outside the configured registry or integration interceptor. See [Integrations](integrations.md) and [Safety](safety.md).
