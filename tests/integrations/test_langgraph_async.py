"""Offline sync/async coverage for the native LangGraph integration."""

import asyncio
from typing import Any

import pytest

langgraph_prebuilt = pytest.importorskip("langgraph.prebuilt")
pytest.importorskip("langchain_core")

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from agentfault.integrations.langgraph import (
    LangGraphScenarioRunner,
    LangGraphToolCallInterceptor,
)
from agentfault.testing import (
    BeforeModelCall,
    ModelTimeoutFault,
    Scenario,
    ToolTimeoutFault,
)
from agentfault.testing.triggers import BeforeTool


def tool_call_message(name: str = "lookup", args: dict[str, Any] | None = None) -> AIMessage:
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


def test_langgraph_toolnode_async_hook_records_timing_and_trajectory() -> None:
    world = {"calls": 0}

    @tool
    async def lookup(query: str) -> str:
        """Return a test value without any external network access."""
        world["calls"] += 1
        return f"found:{query}"

    interceptor = LangGraphToolCallInterceptor(environment=world)
    tool_node = langgraph_prebuilt.ToolNode(
        [lookup],
        awrap_tool_call=interceptor.awrap_tool_call,
    )

    response = asyncio.run(tool_node.ainvoke([tool_call_message()]))

    assert isinstance(response[0], ToolMessage)
    assert response[0].content == "found:hello"
    assert world["calls"] == 1
    assert len(interceptor.trajectory) == 1
    assert interceptor.trajectory[0].observation == "found:hello"
    assert [event.outcome for event in interceptor.trace.events] == [
        "started",
        "succeeded",
    ]
    assert interceptor.trace.events[1].duration_ms is not None


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
    assert [event.outcome for event in result.events if event.kind == "model_call"] == [
        "started",
        "failed",
    ]
    assert any(event.kind == "fault" and event.outcome == "injected" for event in result.events)
    assert result.events[-1].outcome == "error"


def test_langgraph_runner_rejects_uninstrumented_model_fault_schedules() -> None:
    class GraphWithoutModelBoundary:
        async def ainvoke(self, inputs: Any, config: Any | None = None) -> dict[str, str]:
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
    tool_node = langgraph_prebuilt.ToolNode(
        [lookup],
        awrap_tool_call=interceptor.awrap_tool_call,
    )
    scenario = Scenario(
        name="async tool timeout",
        agent=tool_node,
        environment=world,
        faults=[(BeforeTool("lookup"), ToolTimeoutFault("tool timed out"))],
    )

    result = asyncio.run(
        LangGraphScenarioRunner(scenario, interceptor).arun([tool_call_message()])
    )

    assert result.error is None
    assert world["calls"] == 0
    assert not result.trajectory[0].succeeded
    assert result.trajectory[0].error is not None
    assert result.trajectory[0].error["type"] == "TimeoutError"
    assert any(event.kind == "fault" for event in result.events)
