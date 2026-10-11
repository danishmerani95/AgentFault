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

AgentFault provides a `LangGraphToolCallInterceptor` for LangGraph's native `ToolNode(wrap_tool_call=...)` hook, plus a `LangGraphScenarioRunner` that evaluates existing AgentFault assertions against the tool-call trajectory.

Install LangGraph separately (it remains an optional dependency):

```bash
uv run --with "langgraph>=1.0,<2" python -m examples.langgraph_integration
uv run --with "langgraph>=1.0,<2" pytest tests/examples/test_langgraph_integration.py
```

The runnable example uses a deterministic scripted graph node rather than a live LLM, so it does not need an API key. It looks up an account, changes its status to suspended after the lookup, then has the graph re-check the account. The test asserts the refund tool is never called.

For an existing graph, construct the interceptor using the same environment and perturbations as the scenario, pass it to the `ToolNode` that actually executes the tools, compile the graph, and invoke it through `LangGraphScenarioRunner(scenario, interceptor)`. Wrapping only a completed `graph.invoke(...)` call is insufficient because the runner must intercept each tool execution.

The initial integration supports synchronous `invoke` with sequential calls routed through the configured `ToolNode`. Parallel tool-call ordering, async `ainvoke`, and tools executed through other nodes are not yet supported.

## Important constraints

- The adapter and registered tool names must agree exactly.
- Only calls executed via AgentFault’s tool executor are present in its trajectory and can be intercepted by `BeforeTool` / `AfterTool` perturbations.
- If the framework runs tools internally, uses parallel tool calls, maintains a complex graph state, or emits nonstandard tool observations, the adapter must explicitly handle those semantics. The current core loop supports one proposed call at a time.
- AgentFault does not automatically turn arbitrary production tool functions into safe test tools. Use isolated test dependencies and avoid live side effects.
- A custom adapter is a small integration layer, not proof that every version or execution mode of every framework is supported. Framework-specific adapters need integration tests against their supported versions.
