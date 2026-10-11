# Integrations

Agent Fault's integration boundary is the execution of tools. It needs to observe tool calls so it can record a trajectory and apply perturbations between decisions. The right integration depends on which component owns the tool loop.

## Generic Agent contract

For the generic custom-scenario runner and benchmark API, implement `agentfault.agent.Agent`:

```python
from typing import Any

from agentfault.agent import Agent
from agentfault.tools import ToolCall


class MyAgent(Agent):
    def next_action(self, observation: Any) -> ToolCall | None:
        # Decide based on the latest observation.
        # Return a ToolCall to request a registered tool, or None to stop.
        ...
```

The adapter proposes a tool call; it must not execute that tool. Give the concrete implementations to a `ToolRegistry` and run a `Scenario` with `ScenarioRunner`. The first observation is `None`; later observations are the result from the most recent tool execution or a structured tool-error observation.

For the benchmark API, the factory signature is `factory(task: str, tools: list[Tool]) -> Agent`. The benchmark runner creates each case's isolated scenario and tool set, calls the factory, and executes the returned Agent-compatible object. See the runnable [OpenAI benchmark example](../examples/openai_benchmark.py).

## OpenAI

The package includes an OpenAI integration with `OpenAIAgent` and `to_openai_tools`. The repository example shows a factory that builds a new model-backed agent for each benchmark case.

From a repository checkout:

```bash
uv sync --extra dev
export OPENAI_API_KEY=...
uv run python -m examples.openai_benchmark
```

The tool implementations are still bound to Agent Fault's synthetic commerce environment. The model API call is external, but this example does not call real merchants, checkout, or payment services. The example scripts live in the Git repository and are not packaged into the installed PyPI wheel.

## LangChain chat models

The [LangChain benchmark example](../examples/langchain_benchmark.py) uses `ChatOpenAI` and `bind_tools` to obtain one tool-call decision at a time. It translates that decision to Agent Fault's `Agent` contract; Agent Fault then executes the registered tool, records the result, applies scheduled perturbations, and passes the observation to the next model call.

Run it from a repository checkout with:

```bash
uv sync --extra dev
export OPENAI_API_KEY=...
uv run --with "langchain-openai>=0.3,<2" python -m examples.langchain_benchmark
```

This is a chat-model adapter, **not** a transparent wrapper around an arbitrary LangChain `AgentExecutor` or every LangChain application. If another framework component owns the tool loop, Agent Fault will only observe calls routed through its configured execution hook. The example disallows parallel tool calls so that a perturbation can occur between decisions.

## LangGraph

LangGraph owns its own graph execution loop, so wrap the relevant `ToolNode` with Agent Fault's `LangGraphToolCallInterceptor` and pass the scenario and interceptor to `LangGraphScenarioRunner`. A complete deterministic example is in [`examples/langgraph_integration.py`](../examples/langgraph_integration.py).

Run it from the repository:

```bash
uv run --with "langgraph>=1.0,<2" python -m examples.langgraph_integration
```

The example uses a real `StateGraph` and `ToolNode`, but a scripted decision node and a fake support backend; no model API key is required.

**Current limitation in v0.1.0:** the native integration supports synchronous `invoke`, sequential tool calls routed through the configured `ToolNode`. Async execution, parallel ordering, and other tool execution paths are not supported yet. The native LangGraph runner is for custom scenarios; the first benchmark API expects an `Agent`-compatible factory.

## Build another adapter

For a new framework, decide first who executes the tools.

- If Agent Fault can own the execution loop, implement `Agent.next_action(observation)` and register the real test tool implementations in `ToolRegistry`.
- If the framework owns the execution loop, instrument its concrete tool-execution path. Add tests for the execution modes and framework versions you intend to support.
- Make it explicit when some tools, nodes, or side effects bypass the interceptor. An adapter should not claim coverage it cannot observe.

Keep the adapter thin: translate framework-specific messages into tool names and argument dictionaries, then preserve the framework's errors and execution semantics as far as the supported API permits.

## Safety checklist

Before connecting an agent, confirm that:

- All registered tools point at fixtures, fake services, or a disposable sandbox.
- Credentials cannot reach production write endpoints.
- Every consequential tool call goes through the configured executor or interceptor.
- Perturbations cannot leak state between scenarios.
- The adapter is tested against the exact sync/async, retry, and parallel behavior used by the application.

See [Safety](safety.md) for the scope of isolation and [Custom Scenarios](custom-scenarios.md) for failure recipes.
