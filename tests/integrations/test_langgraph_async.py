"""Offline sync/async coverage for the native LangGraph integration."""

import asyncio
from typing import Any

import pytest

langgraph_prebuilt = pytest.importorskip("langgraph.prebuilt")
pytest.importorskip("langchain_core")
pytest.importorskip("langgraph.graph")

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.tools import tool  # noqa: E402
from langgraph.graph import END, START, MessagesState, StateGraph  # noqa: E402

from agentfault.integrations.langgraph import (  # noqa: E402
    LangGraphScenarioRunner,
    LangGraphToolCallInterceptor,
)
from agentfault.testing import (  # noqa: E402
    BeforeModelCall,
    ModelTimeoutFault,
    Scenario,
    ToolTimeoutFault,
)
from agentfault.testing.triggers import BeforeTool  # noqa: E402


def tool_call_message(
    name: str = "lookup",
    args: dict[str, Any] | None = None,
) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args or {"query": "hello"},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )


def build_async_graph(interceptor: LangGraphToolCallInterceptor, lookup: Any) -> Any:
    """Build a real graph that routes a scripted decision through async ToolNode."""
    tool_node = langgraph_prebuilt.ToolNode(
        [lookup],
        wrap_tool_call=interceptor,
        awrap_tool_call=interceptor.awrap_tool_call,
    )

    def scripted_agent(state: MessagesState) -> dict[str, list[AIMessage]]:
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            return {"messages": [tool_call_message()]}
        return {"messages": [AIMessage(content="finished test turn")]}

    def route_after_agent(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    builder = StateGraph(MessagesState)
    builder.add_node("agent", scripted_agent)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile()


def test_langgraph_toolnode_async_hook_records_timing_and_trajectory() -> None:
    world = {"calls": 0}

    @tool
    async def lookup(query: str) -> str:
        """Return a test value without any external network access."""
        world["calls"] += 1
        return f"found:{query}"

    interceptor = LangGraphToolCallInterceptor(environment=world)
    graph = build_async_graph(interceptor, lookup)
    scenario = Scenario(name="async lookup", agent=graph, environment=world)

    result = asyncio.run(
        LangGraphScenarioRunner(scenario, interceptor).arun(
            {"messages": [HumanMessage(content="look up a test value")]}
        )
    )

    assert result.error is None
    assert result.passed
    assert world["calls"] == 1
    assert len(result.trajectory) == 1
    assert result.trajectory[0].observation == "found:hello"
    tool_events = [event for event in result.events if event.kind == "tool_call"]
    assert [event.outcome for event in tool_events] == ["started", "succeeded"]
    assert tool_events[1].duration_ms is not None
    assert result.events[-1].outcome == "passed"


def test_langgraph_async_model_faults_flow_through_scenario_runner() -> None:
    interceptor = LangGraphToolCallInterceptor(environment={})

    class AsyncGraph:
        async def ainvoke(self, inputs: Any, config: Any | None = None) -> Any:
            async def model_call() -> AIMessage:
                return AIMessage(content="should not execute")

            return await interceptor.ainvoke_model(model_call)

    scenario = Scenario(
        name="model timeout in async graph",
        agent=AsyncGraph(),
        environment={},
        model_faults=[
            (BeforeModelCall(1), ModelTimeoutFault("async model timeout"))
        ],
    )
    runner = LangGraphScenarioRunner(scenario, interceptor)

    result = asyncio.run(runner.arun({"messages": []}))

    assert not result.passed
    assert isinstance(result.error, TimeoutError)
    assert str(result.error) == "async model timeout"
    assert [
        event.outcome for event in result.events if event.kind == "model_call"
    ] == ["started", "failed"]
    assert any(
        event.kind == "fault" and event.outcome == "injected"
        for event in result.events
    )
    assert result.events[-1].outcome == "error"


def test_langgraph_runner_rejects_uninstrumented_model_fault_schedules() -> None:
    class GraphWithoutModelBoundary:
        async def ainvoke(
            self, inputs: Any, config: Any | None = None
        ) -> dict[str, str]:
            return {"answer": "model hook was bypassed"}

    interceptor = LangGraphToolCallInterceptor(environment={})
    scenario = Scenario(
        name="missing model boundary",
        agent=GraphWithoutModelBoundary(),
        environment={},
        model_faults=[
            (BeforeModelCall(1), ModelTimeoutFault("not reached"))
        ],
    )
    result = asyncio.run(LangGraphScenarioRunner(scenario, interceptor).arun({}))

    assert not result.passed
    assert isinstance(result.error, RuntimeError)
    assert "invoke_model/ainvoke_model" in str(result.error)


def test_langgraph_async_tool_timeout_returns_error_tool_message() -> None:
    world = {"calls": 0}

    @tool
    async def lookup(query: str) -> str:
        """Return a test value if invoked."""
        world["calls"] += 1
        return f"found:{query}"

    interceptor = LangGraphToolCallInterceptor(environment=world)
    graph = build_async_graph(interceptor, lookup)
    scenario = Scenario(
        name="async tool timeout",
        agent=graph,
        environment=world,
        faults=[(BeforeTool("lookup"), ToolTimeoutFault("tool timed out"))],
    )

    result = asyncio.run(
        LangGraphScenarioRunner(scenario, interceptor).arun(
            {"messages": [HumanMessage(content="look up a test value")]}
        )
    )

    assert result.error is None
    assert world["calls"] == 0
    assert len(result.trajectory) == 1
    assert not result.trajectory[0].succeeded
    assert result.trajectory[0].error is not None
    assert result.trajectory[0].error["type"] == "TimeoutError"
    assert any(event.kind == "fault" for event in result.events)
