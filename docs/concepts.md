# Core Concepts

Agent Fault tests whether an agent's behavior remains acceptable when the environment changes during execution. The core vocabulary is deliberately small.

## The execution model

```text
agent chooses a tool call
        ↓
Agent Fault executes a registered tool
        ↓
tool result is recorded
        ↓
matching trigger applies a perturbation
        ↓
agent receives the observation and chooses again
        ↓
assertions evaluate the completed run
```

A perturbation changes the environment after or before a matching tool call; it does not make a decision for the agent. Assertions evaluate the evidence after the run.

## Main concepts

### Agent

An object implementing `agentfault.agent.Agent`. Its `next_action(observation)` method returns a `ToolCall(name, arguments)` or `None` when it is done. The initial observation is `None`; later observations contain tool results or tool-error information.

The adapter should propose an action, not execute it itself. Agent Fault must retain control of the execution path if it is to record and perturb calls reliably.

### Tool and ToolRegistry

A `Tool` packages a name, description, and Python callable. A `ToolRegistry` maps names to implementations. A generic `ScenarioRunner` executes the agent's calls through this registry, which is also the boundary where tool calls can be recorded and modified.

If your production agent executes tools in another framework-owned loop, use an integration that intercepts that execution path rather than assuming a generic adapter will see it. See [Integrations](integrations.md).

### Environment

The environment is the state your tools read and update: for example, offer prices, inventory, account status, tickets, documents, or job state. Tests should provide a fresh, isolated environment per scenario so that runs do not contaminate each other.

Agent Fault does not sandbox arbitrary side effects. Your environment and tool implementations determine what a tool can actually affect.

### Scenario

A `Scenario` groups:
- `name`: a descriptive identifier.
- `agent`: the decision-making agent or integration-supported graph.
- `environment`: the state being tested.
- `perturbations`: trigger/perturbation pairs to apply during a run.
- `assertions`: checks that define acceptable behavior.

Use scenarios for application-specific failure modes. For the constructors and patterns, see [Custom Scenarios](custom-scenarios.md).

### Trigger

A trigger determines *when* a perturbation applies. The built-in `BeforeTool("tool_name")` matches before a named tool executes; `AfterTool("tool_name")` matches after that tool has successfully executed. Triggers match tool names, so spelling and routing matter.

### Perturbation

A perturbation changes the environment or induces a tool failure. Built-in perturbations include `ChangePrice`, `ChangeInventory`, and `FailTool`; you can subclass `Perturbation` to model your domain's state changes.

A scheduled `FailTool` is a tool-execution fault, not a general agent/provider exception. See [Custom Scenarios](custom-scenarios.md) for examples and behavior details.

### Assertion

An assertion evaluates evidence from the completed run. Built-ins include `MaxPriceAssertion` for the synthetic commerce environment and `ProhibitedActionAssertion` for checking that a named action was not successfully executed. Implement `Assertion.check(context)` for application-specific requirements.

A good assertion should encode a user or system invariant—not simply whether the agent produced a plausible explanation.

### Trajectory and result

A scenario result contains `passed`, assertion results, a trajectory of tool calls and observations, and a possible terminal error. The trajectory helps explain *why* a scenario passed or failed.

For results, failure modes, and debugging steps, see [Results and Troubleshooting](results-and-troubleshooting.md).

## Custom scenarios versus benchmarks

A **custom scenario** targets a failure mode in your application. You choose the environment, perturbation timing, and acceptance criteria.

A **benchmark** applies a versioned collection of scenarios to an agent factory, running each case with a fresh scenario/environment. That enables repeatable comparisons across agent versions. The first built-in pack is the five-case `buying-agent@1.0.0` suite; see [Benchmarks](benchmarks.md).

## Execution boundary

Agent Fault can only record, fail, or perturb tool calls routed through its configured executor or integration hook. Calls made directly from an agent, a graph node, a callback, or an external service outside that path are not automatically observed. This boundary is especially important for production-like testing; read [Safety](safety.md) before integrating live systems.
