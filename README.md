# AgentFault

**Break the world around your agent. Verify its behavior.**

AgentFault is an open-source reliability testing toolkit for tool-using AI agents. It lets you change the environment *during* an agent's task—make a tool fail, change a record, revoke a permission, or alter an offer—and verify what the agent does next.

Most agent tests ask whether a model produced a good answer for a given input. AgentFault tests a different question:

> **When the world changes after the agent has made a decision, does it still behave correctly?**

Use it to test stale assumptions, recovery from tool failures, and consequential actions that become unsafe mid-run. Tests can run alongside your existing Python tests and CI.

> **Status: Alpha.** APIs may change. LangGraph support is experimental and currently covers synchronous `invoke` with sequential tool calls.

## What you can test

- **State changes:** An account is suspended, inventory reaches zero, or a document changes after the agent reads it.
- **Tool failures:** A tool times out or fails once. Does the agent retry, choose a safe alternative, or stop?
- **Safety at action time:** A price rises or a permission changes before the agent executes a purchase, refund, deletion, or other consequential action.
- **Behavioral contracts:** Assert which tools the agent did or did not call, whether a failure was recovered from, and what changed in the test environment.

AgentFault is not a model-training framework or a general chat-quality leaderboard. It focuses on **controllable, stateful interventions and evidence from actual tool execution**.

## How it works

A scenario combines four parts:

1. **Your agent** — the decision-making code you want to test.
2. **A test environment and tools** — real application logic connected to fixtures, fakes, or a safe sandbox.
3. **A perturbation** — what changes, and when it changes (for example, after `lookup_account`).
4. **Assertions** — the behaviors or outcomes that must hold after the change.

AgentFault runs the scenario, records intercepted tool calls and observations, applies scheduled perturbations, and evaluates assertions against the resulting trajectory. The test result gives you pass/fail evidence, not just a final model response.

## Quick start

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

Clone the repository and install the development environment:

```bash
git clone https://github.com/danishmerani95/AgentFault.git
cd AgentFault
uv sync --extra dev
```

Run a scenario:

```bash
uv run agentfault run examples.scenarios.state_change:build_scenario
```

Print JSON output or set a tool-execution limit:

```bash
uv run agentfault run examples.scenarios.state_change:build_scenario --json
uv run agentfault run examples.scenarios.state_change:build_scenario --max-steps 25
```

CLI exit codes are `0` for passed assertions, `1` for a scenario that failed its assertions, and `2` for a loading or execution error.

## Example: test your agent when the world changes

Imagine your agent looks up an account and sees it is active. Before it issues a refund, the account becomes suspended. The test should verify the agent checks the changed state and never issues the refund.

A scenario expresses the disturbance and behavioral contract explicitly:

```python
scenario = Scenario(
    name="account suspended after lookup",
    agent=agent_under_test,
    environment=test_environment,
    perturbations=[
        (AfterTool("lookup_account"), SuspendAccount()),
    ],
    assertions=[
        ProhibitedActionAssertion("issue_refund"),
    ],
)
```

Here, `SuspendAccount` is a project-defined perturbation that changes the test environment. `agent_under_test` and `test_environment` are yours. Use fake or sandboxed dependencies for tests that could trigger real side effects.

See the [scenario library](examples/scenarios/) for runnable examples involving changing inventory, a failed tool call, and an intentionally unsafe purchase.

## Connect an existing agent

You don't need to rewrite your agent's decision logic. AgentFault needs a way to observe and control individual tool executions. The integration point depends on how your agent is orchestrated.

### LangGraph

AgentFault provides a `LangGraphToolCallInterceptor` for LangGraph's `ToolNode(wrap_tool_call=...)` hook and a `LangGraphScenarioRunner` that evaluates AgentFault assertions against the recorded tool-call trajectory.

The basic integration is to pass the interceptor when constructing the `ToolNode` that executes the tools under test, and then invoke your compiled graph through the AgentFault runner:

```python
from agentfault.integrations.langgraph import (
    LangGraphScenarioRunner,
    LangGraphToolCallInterceptor,
)
from agentfault.testing import Scenario
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.triggers import AfterTool
from langgraph.prebuilt import ToolNode

# Your existing tools, test environment, and graph nodes stay yours.
perturbations = [
    (AfterTool("lookup_account"), SuspendAccount()),
]
interceptor = LangGraphToolCallInterceptor(
    environment=test_environment,
    perturbations=perturbations,
)

# Use this ToolNode in your existing StateGraph.
tool_node = ToolNode(
    [lookup_account_tool, issue_refund_tool],
    wrap_tool_call=interceptor,
)
# ...build/compile your existing graph using tool_node...

scenario = Scenario(
    name="account suspended after lookup",
    agent=compiled_graph,
    environment=test_environment,
    perturbations=perturbations,
    assertions=[ProhibitedActionAssertion("issue_refund")],
)

result = LangGraphScenarioRunner(
    scenario, interceptor
).run({"messages": [HumanMessage(content="Process the refund")]})

assert result.passed, [
    item.message for item in result.assertions if not item.passed
]
```

The example above shows the integration seam; names such as `SuspendAccount`, `test_environment`, and your tool variables represent your application's own fixtures and functions.

Try the complete deterministic example (no LLM API key required):

```bash
python -m pip install "langgraph>=1.0,<2"
uv run python -m examples.langgraph_integration
uv run pytest tests/examples/test_langgraph_integration.py
```

It uses a real LangGraph `StateGraph` and `ToolNode`, with a scripted decision node so the test stays deterministic. It demonstrates interception and a state change; it does **not** evaluate a live LLM's reasoning quality.

**Current LangGraph limits:** synchronous `invoke`, sequential tool calls, and calls routed through the configured `ToolNode`. Async `ainvoke`, parallel tool-call ordering, and tools executed outside that node are not yet supported.

### OpenAI SDK, LangChain, Claude, and custom agents

- **OpenAI SDK:** AgentFault includes an OpenAI tool-calling agent adapter that can be configured with your prompts, tools, and model.
- **LangChain:** no dedicated built-in adapter yet. A custom adapter must preserve the tool-call/tool-result cycle and route tested tool execution through AgentFault.
- **Claude / Anthropic:** no dedicated built-in adapter yet. The native `tool_use` / tool-result message cycle needs a provider-specific adapter.
- **Other agents:** implement the small AgentFault `Agent` contract by translating the agent's proposed tool call to `ToolCall` and returning observations on the next decision. The agent must not execute the intercepted tool internally.

See the [custom adapter guide](docs/custom-adapters.md) and [custom adapter example](examples/custom_adapter.py).

## Use it from pytest

For scenarios that use AgentFault's standard `ScenarioRunner`, the pytest plugin lets you keep assertions in your existing test suite:

```python
import pytest
from agentfault.testing import ScenarioResult


@pytest.mark.agentfault("my_scenarios.checkout:build_scenario")
def test_checkout_agent_is_safe(
    agentfault_result: ScenarioResult,
) -> None:
    assert agentfault_result.passed, [
        item.message
        for item in agentfault_result.assertions
        if not item.passed
    ]
```

For a custom runner such as `LangGraphScenarioRunner`, call it directly from a normal pytest test—the included [LangGraph integration test](tests/examples/test_langgraph_integration.py) demonstrates this pattern.

## Examples and developer docs

- [State change during a task](examples/scenarios/state_change.py)
- [Tool failure and recovery](examples/scenarios/tool_failure_recovery.py)
- [Unsafe purchase after a price increase](examples/scenarios/unsafe_purchase.py) — an intentionally failing scenario
- [Custom adapter example](examples/custom_adapter.py)
- [LangGraph integration example](examples/langgraph_integration.py)
- [Custom adapter guide](docs/custom-adapters.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Design principle

**Specific outside, general inside.** The initial examples use commerce, but the core idea applies wherever an agent uses tools to change or inspect a world: support, operations, research, workflow automation, and internal business systems.

Start with one failure mode you care about. Make it reproducible. Assert the behavior that must hold. Then run it every time your agent changes.
