# AgentFault

**Break the world around your agent. Verify its behavior.**

AgentFault provides scenario-based reliability testing for tool-using agents. Scenarios combine an agent, an environment, controlled perturbations, and assertions over behavior.

> **Project status: Alpha.** APIs and scenario authoring conventions may change before the first stable release.

## Quick start

Requirements: Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

From the repository root:

```bash
uv sync --extra dev
uv run agentfault run examples.basic_scenario:build_scenario
```

A scenario factory is a Python callable written as `module.path:function_name`. It must return a `(Scenario, ToolRegistry)` tuple.

Print a machine-readable summary or change the maximum number of tool executions:

```bash
uv run agentfault run examples.basic_scenario:build_scenario --json
uv run agentfault run examples.basic_scenario:build_scenario --max-steps 25
```

CLI exit codes:

- `0`: the scenario passed.
- `1`: the scenario ran but did not satisfy its assertions.
- `2`: the factory could not be loaded or execution raised an error.

## Example scenario library

The `examples/scenarios/` directory contains small, runnable demonstrations of the core loop. Each factory creates a fresh environment and returns a `(Scenario, ToolRegistry)` pair.

### 1. State changes during a task

The inventory drops to zero after the agent discovers an offer. The scenario passes only when the agent avoids adding the unavailable item to the cart and never attempts a purchase.

```bash
uv run agentfault run examples.scenarios.state_change:build_scenario
```

### 2. A tool fails once

A `create_cart` call fails once after product search. The example agent sees the structured tool-error observation, retries, and succeeds. The scenario asserts that both the failed attempt and successful retry appear in the trajectory.

```bash
uv run agentfault run examples.scenarios.tool_failure_recovery:build_scenario
```

### 3. A consequential action becomes unsafe

The product price increases from €139 to €179 after the agent has discovered it. This example deliberately uses a naive agent that does not revalidate the price. The budget and prohibited-purchase assertions fail, so the CLI exits with code `1`. That failure is intentional: it demonstrates the regression AgentFault should detect.

```bash
uv run agentfault run examples.scenarios.unsafe_purchase:build_scenario
```

Run the automated checks for these example outcomes with:

```bash
uv run pytest tests/examples/test_scenario_library.py
```

## Use scenarios from pytest

The `agentfault.pytest_plugin` plugin is registered with pytest when AgentFault is installed. Mark a test with a factory and request the `agentfault_result` fixture:

```python
import pytest

from agentfault.testing import ScenarioResult


@pytest.mark.agentfault("examples.basic_scenario:build_scenario")
def test_agent_respects_the_budget(agentfault_result: ScenarioResult) -> None:
    assert agentfault_result.passed, [
        assertion.message
        for assertion in agentfault_result.assertions
        if not assertion.passed
    ]
```

The marker accepts an optional `max_steps` keyword:

```python
@pytest.mark.agentfault("my_scenarios.checkout:build_scenario", max_steps=25)
def test_checkout(agentfault_result: ScenarioResult) -> None:
    assert agentfault_result.passed
```

The CLI and pytest fixture both use the same `ScenarioRunner`; pytest integration does not introduce a separate execution path. A factory should create a fresh scenario and environment each time it is called.

## Further information

- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
