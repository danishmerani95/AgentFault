"""Run any built-in Agent Fault suite with a native LangGraph execution loop.

Install framework extras and set the model API key, then choose a suite:
    export OPENAI_API_KEY=...
    export AGENTFAULT_BENCHMARK_SUITE=customer-support-agent
    uv run --with "langchain-openai>=0.3,<2" --with "langgraph>=1.0,<2" \
        python -m examples.langgraph_benchmark

Unlike the generic Agent adapter, this example lets LangGraph's StateGraph and
ToolNode own the tool loop and uses BenchmarkRunner's scenario_executor extension.
"""

import json
import os
from typing import Any

from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkRunner
from agentfault.testing import Scenario
from agentfault.tools import Tool, ToolRegistry
from agentfault.integrations.langgraph import (
    LangGraphScenarioRunner,
    LangGraphToolCallInterceptor,
)
from examples.benchmark_suites import load_benchmark_suite


def create_chat_model() -> Any:
    """Construct the external chat model. Override this function in tests."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("AGENTFAULT_LANGGRAPH_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


class LangGraphBenchmarkAgent(Agent):
    """Handle to a compiled graph and its interceptor.

    This object is intentionally not driven by Agent.next_action. BenchmarkRunner
    must use langgraph_scenario_executor so LangGraph, not AgentFault's generic
    executor, performs the actual tool calls.
    """

    def __init__(
        self,
        *,
        graph: Any,
        interceptor: LangGraphToolCallInterceptor,
        task: str,
    ) -> None:
        self.graph = graph
        self.interceptor = interceptor
        self.task = task

    def next_action(self, observation: Any) -> None:
        del observation
        raise RuntimeError(
            "LangGraphBenchmarkAgent requires scenario_executor="
            "langgraph_scenario_executor."
        )

    def invoke(self, inputs: Any, config: Any | None = None) -> Any:
        return self.graph.invoke(inputs, config=config)


def build_langgraph_agent(
    task: str,
    tools: list[Tool],
    *,
    model: Any | None = None,
) -> LangGraphBenchmarkAgent:
    """Build an agent graph around supplied test tools and a chat model."""
    from langchain_core.messages import AIMessage
    from langchain_core.tools import StructuredTool
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode

    langchain_tools = [
        StructuredTool.from_function(
            func=tool.function,
            name=tool.name,
            description=tool.description,
        )
        for tool in tools
    ]
    interceptor = LangGraphToolCallInterceptor(environment={}, perturbations=[])
    tool_node = ToolNode(langchain_tools, wrap_tool_call=interceptor)
    selected_model = (model if model is not None else create_chat_model()).bind_tools(
        langchain_tools,
        parallel_tool_calls=False,
    )

    def call_model(state: MessagesState) -> dict[str, list[Any]]:
        response = selected_model.invoke(state["messages"])
        if not isinstance(response, AIMessage):
            raise TypeError("LangGraph benchmark model must return an AIMessage.")
        return {"messages": [response]}

    def route_after_model(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_model, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return LangGraphBenchmarkAgent(
        graph=builder.compile(),
        interceptor=interceptor,
        task=task,
    )


def langgraph_agent_factory(task: str, tools: list[Tool]) -> Agent:
    return build_langgraph_agent(task, tools)


def langgraph_scenario_executor(
    scenario: Scenario,
    tool_registry: ToolRegistry,
    max_steps: int,
):
    """Execute a benchmark case through the native LangGraph ToolNode hook."""
    del tool_registry  # The compiled graph executes its configured LangChain tools.
    agent = scenario.agent
    if not isinstance(agent, LangGraphBenchmarkAgent):
        raise TypeError(
            "Expected LangGraphBenchmarkAgent; use langgraph_agent_factory."
        )
    agent.interceptor.environment = scenario.environment
    agent.interceptor.perturbations = scenario.perturbations
    agent.interceptor.max_steps = max_steps

    from langchain_core.messages import HumanMessage

    inputs = {"messages": [HumanMessage(content=agent.task)]}
    return LangGraphScenarioRunner(scenario, agent.interceptor).run(inputs)


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY to run this LangGraph benchmark example.")
    suite_id = os.getenv("AGENTFAULT_BENCHMARK_SUITE", "buying-agent")
    model_name = os.getenv("AGENTFAULT_LANGGRAPH_MODEL", "gpt-4o-mini")
    result = BenchmarkRunner(max_steps=20).run(
        load_benchmark_suite(suite_id),
        langgraph_agent_factory,
        agent_name=f"langgraph:{model_name}",
        scenario_executor=langgraph_scenario_executor,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
