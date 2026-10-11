# Connecting an agent

AgentFault needs control over individual tool executions so it can record the trajectory and apply a perturbation between decisions.

## Agents using the Agent contract

Implement `agentfault.agent.Agent`:

- `next_action(observation)` receives the latest tool result (or `None` at the start).
- Return a `ToolCall(name, arguments)` when the agent proposes a tool call.
- Return `None` when the agent is done.
- Do not execute the proposed tool inside the adapter. Register its implementation in the scenario's `ToolRegistry`; AgentFault invokes it and returns the observation on the next decision.

The benchmark API accepts a factory for this contract. AgentFault includes a generic OpenAI tool-calling adapter; see [the benchmark example](../examples/openai_benchmark.py).

## LangGraph

LangGraph owns its own graph execution loop, so use the native integration: wrap the relevant `ToolNode` with `LangGraphToolCallInterceptor` and invoke the compiled graph with `LangGraphScenarioRunner`. See [the runnable custom-scenario example](../examples/langgraph_integration.py).

Current limitations: synchronous `invoke`, sequential calls through the configured `ToolNode`; async execution, parallel ordering, and tools executed by other nodes are not supported yet. The native LangGraph runner is for custom scenarios; the first BenchmarkRunner release accepts agents through the generic `Agent` contract.

## Safety

Use fresh test fixtures, fake services, or a sandbox—not live purchase, payment, refund, or customer systems. AgentFault can intercept only tool calls that are routed through its configured executor or integration hook. Provider/framework adapters should have integration tests for the exact versions and execution modes they claim to support.
