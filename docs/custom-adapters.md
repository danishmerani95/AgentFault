# Custom agent adapters

AgentFault does not require an agent to be built with a specific model provider or framework. It needs a small adapter that presents the agent’s decision loop through the `Agent` contract:

- `next_action(observation)` receives the most recent tool observation (or `None` at the start).
- It returns an AgentFault `ToolCall(name, arguments)` when the agent wants to execute a tool.
- It returns `None` when the agent has finished.
- It must not execute the requested tool itself. AgentFault’s runner executes calls through the supplied `ToolRegistry`, records the trajectory, and triggers perturbations around execution.

This is the seam that lets AgentFault control the world between tool calls.

## Reference example

See [`examples/custom_adapter.py`](../examples/custom_adapter.py). It wraps a dummy support agent whose native interface returns dictionaries, converts those dictionaries to `ToolCall`, and tests that the agent rechecks account status before issuing a refund. The fake environment is isolated from real customer/payment systems.

Run the example from the repository root:

```bash
uv run python -m examples.custom_adapter
```

Run its regression test:

```bash
uv run pytest tests/examples/test_custom_adapter.py
```

## Adapting an existing framework

A typical adapter does four things:

1. Ask the framework/model for its next proposed tool call.
2. Translate its native tool name and arguments to `ToolCall`.
3. Return that call without executing the tool.
4. Translate the observation returned by AgentFault into the native tool-result/message format on the next `next_action` invocation.

Tool functions should be registered in the `ToolRegistry` used by the scenario. In many projects, these can be thin wrappers around the existing application functions. For safe, deterministic tests, point them at test doubles, fixtures, or a sandbox rather than production services.

### OpenAI SDK and Claude

For providers that expose an explicit tool-call / tool-result cycle, the adapter can translate provider tool-call messages to `ToolCall`, then append AgentFault’s returned observation as the corresponding tool result before requesting the next model response. AgentFault currently includes an OpenAI adapter; Claude would need a separate adapter for Anthropic’s native content blocks and tool-result message structure.

### LangChain

A LangChain adapter can translate an `AIMessage` with tool calls into `ToolCall` and, on the next invocation, translate the observation into the matching tool result. Avoid invoking a chain that executes all tools internally if the test needs to inject changes between individual calls.

### LangGraph

AgentFault now provides an interceptor for LangGraph's `ToolNode(wrap_tool_call=...)` hook. It records tool calls, applies `BeforeTool` / `AfterTool` perturbations around individual executions, and lets the graph continue with its native `ToolMessage` observations. `LangGraphScenarioRunner` then evaluates the scenario assertions against that recorded trajectory.

Install LangGraph in the test environment (it is not a core AgentFault dependency):

```bash
python -m pip install "langgraph>=1.0,<2"
uv run python -m examples.langgraph_integration
uv run pytest tests/examples/test_langgraph_integration.py
```

The runnable example uses a deterministic scripted graph node instead of a live LLM, so it needs no model API key. It looks up an account, AgentFault changes the account to suspended, the graph rechecks the account through its real `ToolNode`, and the assertion verifies that no refund tool was called.

For an existing graph, pass the interceptor to the `ToolNode` that executes the tools under test, then use `LangGraphScenarioRunner(scenario, interceptor)` around the compiled graph. The graph must route tool calls through that node; wrapping only a completed `graph.invoke(...)` call cannot inject a change between tool calls.

This first integration targets synchronous `invoke` and sequential tool calls. Keep model outputs to one tool call at a time for deterministic interventions. Parallel tool calls, async `ainvoke`, and LangGraph's alternate tool-execution paths require additional handling and are not claimed as supported yet.

## Important constraints

- The adapter and registered tool names must agree exactly.
- Only tool calls that pass through AgentFault's interceptor (or another explicitly supported executor path) are present in its trajectory and can be intercepted by `BeforeTool` / `AfterTool` perturbations.
- The LangGraph adapter records sequential synchronous executions. Parallel tool calls, async `ainvoke`, and tools executed outside the configured `ToolNode` are not yet covered.
- AgentFault does not automatically turn arbitrary production tool functions into safe test tools. Use isolated test dependencies and avoid live side effects.
- A custom adapter is a small integration layer, not proof that every version or execution mode of every framework is supported. Framework-specific adapters need integration tests against their supported versions.
