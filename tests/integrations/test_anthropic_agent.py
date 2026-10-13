"""Offline tests for the Anthropic adapter and model-fault integration."""

from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import pytest

from agentfault.integrations.anthropic import AnthropicAgent, to_anthropic_tools
from agentfault.testing import (
    AfterModelCall,
    BeforeModelCall,
    EmptyModelResponseFault,
    ModelTimeoutFault,
    Scenario,
    ScenarioRunner,
)
from agentfault.tools import Tool, ToolCall, ToolRegistry


class FakeMessages:
    def __init__(
        self,
        responses: Iterable[Any] = (),
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses)
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


class FakeClient:
    def __init__(
        self,
        responses: Iterable[Any] = (),
        error: Exception | None = None,
    ) -> None:
        self.messages = FakeMessages(responses=responses, error=error)


def tool_use(
    name: str = "lookup",
    input_value: dict[str, Any] | None = None,
    call_id: str = "toolu_1",
) -> Any:
    return SimpleNamespace(
        type="tool_use",
        name=name,
        input=input_value or {"query": "hello"},
        id=call_id,
    )


def response(*blocks: Any) -> Any:
    return SimpleNamespace(content=list(blocks))


def make_agent(
    client: FakeClient,
    model_call_executor: Any | None = None,
) -> AnthropicAgent:
    def lookup(query: str) -> str:
        return query

    return AnthropicAgent(
        client=client,
        system_prompt="You are a careful test agent.",
        user_prompt="Look up a test value.",
        tools=[Tool("lookup", "Look up a value.", lookup)],
        model="test-claude",
        model_call_executor=model_call_executor,
    )


def test_converts_agentfault_tool_schema_to_anthropic_format() -> None:
    def lookup(query: str) -> str:
        return query

    converted = to_anthropic_tools([Tool("lookup", "Look up a value.", lookup)])

    assert converted == [
        {
            "name": "lookup",
            "description": "Look up a value.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]


def test_single_tool_use_becomes_agentfault_tool_call() -> None:
    client = FakeClient([response(tool_use())])
    agent = make_agent(client)

    action = agent.next_action(None)

    assert action == ToolCall(name="lookup", arguments={"query": "hello"}, id="toolu_1")
    call = client.messages.calls[0]
    assert call["model"] == "test-claude"
    assert call["tool_choice"] == {
        "type": "auto",
        "disable_parallel_tool_use": True,
    }
    assert call["messages"] == [
        {"role": "user", "content": "Look up a test value."}
    ]


def test_tool_result_is_sent_back_before_the_next_model_decision() -> None:
    client = FakeClient(
        [
            response(tool_use()),
            response(SimpleNamespace(type="text", text="Found it.")),
        ]
    )
    agent = make_agent(client)

    assert agent.next_action(None) is not None
    assert agent.next_action({"result": "hello"}) is None

    assert [message["role"] for message in agent.messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    result_block = agent.messages[2]["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "toolu_1"
    assert result_block["content"] == '{"result": "hello"}'


def test_parallel_tool_uses_are_rejected_before_mutating_history() -> None:
    client = FakeClient([response(tool_use(call_id="toolu_1"), tool_use(call_id="toolu_2"))])
    agent = make_agent(client)

    with pytest.raises(ValueError, match="supports one tool use per response"):
        agent.next_action(None)

    assert [message["role"] for message in agent.messages] == ["user"]


def test_model_fault_schedule_is_applied_at_anthropic_request_boundary() -> None:
    executor_client = FakeClient([response(tool_use())])
    agent = make_agent(executor_client)
    agent.model_call_executor.configure(
        [(BeforeModelCall(1), ModelTimeoutFault("injected Claude timeout"))]
    )

    with pytest.raises(TimeoutError, match="injected Claude timeout"):
        agent.next_action(None)

    assert executor_client.messages.calls == []
    assert agent.model_call_executor.call_count == 1


def test_after_model_fault_can_simulate_empty_anthropic_response() -> None:
    client = FakeClient([response(tool_use())])
    agent = make_agent(client)
    agent.model_call_executor.configure(
        [(AfterModelCall(1), EmptyModelResponseFault())]
    )

    with pytest.raises(ValueError, match="tool_use"):
        agent.next_action(None)

    assert len(client.messages.calls) == 1


def test_scenario_runner_applies_model_fault_schedule_to_anthropic_agent() -> None:
    client = FakeClient([response(tool_use())])
    agent = make_agent(client)
    scenario = Scenario(
        name="Claude model timeout",
        agent=agent,
        environment={},
        model_faults=[
            (BeforeModelCall(1), ModelTimeoutFault("scenario injected timeout"))
        ],
    )
    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert not result.passed
    assert isinstance(result.error, TimeoutError)
    assert str(result.error) == "scenario injected timeout"
    assert result.trajectory == []
    assert [event.outcome for event in result.events if event.kind == "model_call"] == [
        "started",
        "failed",
    ]


def test_provider_errors_propagate_and_are_recorded_by_scenario_runner() -> None:
    client = FakeClient(error=RuntimeError("Anthropic provider unavailable"))
    agent = make_agent(client)
    scenario = Scenario(
        name="Claude provider failure",
        agent=agent,
        environment={},
    )

    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert not result.passed
    assert isinstance(result.error, RuntimeError)
    assert str(result.error) == "Anthropic provider unavailable"
    failed_events = [
        event
        for event in result.events
        if event.kind == "model_call" and event.outcome == "failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0].details["error_type"] == "RuntimeError"
