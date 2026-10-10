# AgentFault

**Break the world around your agent. Verify its behavior.**

AgentFault provides scenario-based reliability testing for tool-using agents. Scenarios combine an agent, an environment, controlled perturbations, and assertions over behavior.

## Run a scenario from the CLI

A scenario factory is a Python callable written as `module.path:function_name`. It must return a `(Scenario, ToolRegistry)` tuple.

From the repository root:

```bash
uv sync --extra dev
uv run agentfault run examples.basic_scenario:build_scenario
```

Print a machine-readable summary or change the maximum number of tool executions:

```bash
uv run agentfault run examples.basic_scenario:build_scenario --json
uv run agentfault run examples.basic_scenario:build_scenario --max-steps 25
```

CLI exit codes:

- `0`: the scenario passed.
- `1`: the scenario ran but did not satisfy its assertions.
- `2`: the factory could not be loaded or execution raised an error.

The existing `cartspec` console command remains available as an alias.

## Use scenarios from pytest

The `cartspec.pytest_plugin` plugin is registered with pytest when AgentFault is installed. Mark a test with a factory and request the `agentfault_result` fixture:

```python
import pytest

from cartspec.testing import ScenarioResult


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
