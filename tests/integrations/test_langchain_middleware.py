"""Offline contract tests for the optional native LangChain middleware."""

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("langchain.agents.middleware")

from langchain_core.messages import AIMessage, ToolMessage

from agentfault.integrations.langchain import (
    LangChainScenarioRunner,
    LangChainToolCallInterceptor,
)
from agentfault.testing.faults import (
    EmptyModelResponseFault,
    EmptyResponseFault,
    ModelTimeoutFault,
    ToolTimeoutFault,
)
from agentfault.testing.scenario import Scenario
from agentfault.testing.triggers import AfterModelCall, AfterTool, BeforeModelCall, BeforeTool


def tool_request(name: str = "lookup", args: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        tool_call={"name": name, "args": args or {}, "id": "call-1"}
    )


def test_before_tool_fault_is_returned_to_the_agent_and_recorded() -> None:
    interceptor = LangChainToolCallInterceptor(
        environment={},
        faults=[(BeforeTool("lookup"), ToolTimeoutFault("tool timed out"))],
    )
    called = False

    def handler(request):
        nonlocal called
        called = True
        return ToolMessage(content="ok", tool_call_id="call-1")

    response = interceptor.wrap_tool_call(tool_request(), handler)

    assert not called
    assert isinstance(response, ToolMessage)
    assert response.status == "error"
    assert "tool timed out" in str(response.content)
    assert len(interceptor.trajectory) == 1
    assert interceptor.trajectory[0].error["type"] == "TimeoutError"


def test_after_tool_fault_transforms_the_response_and_records_evidence() -> None:
    interceptor = LangChainToolCallInterceptor(
        environment={},
        faults=[(AfterTool("lookup"), EmptyResponseFault())],
    )

    response = interceptor.wrap_tool_call(
        tool_request(),
        lambda request: ToolMessage(
            content='{"available": true}', tool_call_id="call-1", name="lookup"
        ),
    )

    assert isinstance(response, ToolMessage)
    assert response.content == ""
    assert response.status == "success"
    assert interceptor.trajectory[0].observation is None
    assert interceptor.trajectory[0].error is None


def test_after_tool_perturbation_changes_the_environment_after_observation() -> None:
    environment = {"status": "active"}

    class SuspendAccount:
        def apply(self, target):
            target["status"] = "suspended"

    interceptor = LangChainToolCallInterceptor(
        environment=environment,
        perturbations=[(AfterTool("lookup"), SuspendAccount())],
    )
    response = interceptor.wrap_tool_call(
        tool_request(),
        lambda request: ToolMessage(
            content=environment["status"], tool_call_id="call-1", name="lookup"
        ),
    )

    assert response.content == "active"
    assert environment["status"] == "suspended"
    assert interceptor.trajectory[0].observation == "active"


def test_before_model_fault_prevents_the_model_handler_from_running() -> None:
    interceptor = LangChainToolCallInterceptor(
        environment={},
        model_faults=[(BeforeModelCall(1), ModelTimeoutFault("model timed out"))],
    )
    called = False

    def handler(request):
        nonlocal called
        called = True
        return SimpleNamespace(result=AIMessage(content="ok"))

    with pytest.raises(TimeoutError, match="model timed out"):
        interceptor.wrap_model_call(object(), handler)

    assert not called
    assert interceptor.model_call_executor.call_count == 1


def test_sync_model_fault_can_replace_the_model_response() -> None:
    interceptor = LangChainToolCallInterceptor(
        environment={},
        model_faults=[(AfterModelCall(1), EmptyModelResponseFault())],
    )

    response = interceptor.wrap_model_call(
        object(),
        lambda request: SimpleNamespace(result=AIMessage(content="ok")),
    )

    assert response is None


def test_async_tool_and_model_wrappers_work_without_provider_calls() -> None:
    async def run() -> None:
        interceptor = LangChainToolCallInterceptor(environment={})
        tool_response = await interceptor.awrap_tool_call(
            tool_request(),
            async_handler,
        )
        assert isinstance(tool_response, ToolMessage)
        assert tool_response.content == "async-ok"
        assert len(interceptor.trajectory) == 1

        # The async model executor must await the handler and apply after-call
        # faults to its result, just as the synchronous executor does.
        interceptor.model_call_executor.configure(
            [(AfterModelCall(1), EmptyModelResponseFault())]
        )
        model_response = await interceptor.awrap_model_call(
            object(),
            async_model_handler,
        )
        assert model_response is None
        assert interceptor.model_call_executor.call_count == 1

    async def async_handler(request):
        return ToolMessage(
            content="async-ok",
            tool_call_id="call-1",
            name="lookup",
        )

    async def async_model_handler(request):
        return SimpleNamespace(result=AIMessage(content="ok"))

    asyncio.run(run())


def test_scenario_runner_reports_graph_errors_and_resets_evidence() -> None:
    class BrokenGraph:
        def invoke(self, inputs, config=None):
            raise ValueError("graph failed")

    interceptor = LangChainToolCallInterceptor(environment={})
    scenario = Scenario(
        name="graph error",
        agent=BrokenGraph(),
        environment={},
    )

    result = LangChainScenarioRunner(scenario, interceptor).run({"messages": []})

    assert not result.passed
    assert isinstance(result.error, ValueError)
    assert str(result.error) == "graph failed"
    assert result.trajectory == []
