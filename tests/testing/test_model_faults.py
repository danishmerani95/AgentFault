from typing import Any

import pytest

from agentfault.agent import Agent
from agentfault.testing import (
    AfterModelCall,
    EmptyModelResponseFault,
    BeforeModelCall,
    InjectedModelAPIError,
    MalformedModelResponseFault,
    ModelCallExecutor,
    ModelConnectionFault,
    ModelLatencyFault,
    ModelRateLimitFault,
    ModelServerErrorFault,
    ModelTimeoutFault,
    Scenario,
    ScenarioRunner,
)
from agentfault.tools import ToolCall, ToolRegistry


def test_model_call_executor_faults_before_the_selected_call_once() -> None:
    executor = ModelCallExecutor(
        [(BeforeModelCall(call_number=1), ModelTimeoutFault())]
    )
    invoked: list[bool] = []

    with pytest.raises(TimeoutError, match="model API timeout"):
        executor.execute(lambda: invoked.append(True))

    result = executor.execute(lambda: "response")

    assert result == "response"
    assert invoked == []
    assert executor.call_count == 2


def test_model_call_executor_can_replace_a_response_after_model_returns() -> None:
    executor = ModelCallExecutor(
        [(AfterModelCall(call_number=1), MalformedModelResponseFault("invalid"))]
    )

    first = executor.execute(lambda: {"choices": []})
    second = executor.execute(lambda: {"choices": ["valid"]})

    assert first == "invalid"
    assert second == {"choices": ["valid"]}



def test_empty_model_response_fault_returns_none() -> None:
    executor = ModelCallExecutor(
        [(AfterModelCall(1), EmptyModelResponseFault())]
    )

    assert executor.execute(lambda: "non-empty") is None

def test_model_latency_uses_an_injected_sleeper() -> None:
    sleeps: list[float] = []
    executor = ModelCallExecutor(
        [(BeforeModelCall(), ModelLatencyFault(0.3, sleeper=sleeps.append))]
    )

    assert executor.execute(lambda: "ok") == "ok"
    assert executor.execute(lambda: "ok again") == "ok again"
    assert sleeps == [0.3]


@pytest.mark.parametrize(
    ("fault", "status_code", "error_type"),
    [
        (ModelRateLimitFault(), 429, "rate_limit"),
        (ModelServerErrorFault(), 503, "server_error"),
    ],
)
def test_model_http_faults_expose_provider_neutral_metadata(
    fault: Any, status_code: int, error_type: str
) -> None:
    executor = ModelCallExecutor([(BeforeModelCall(1), fault)])

    with pytest.raises(InjectedModelAPIError) as caught:
        executor.execute(lambda: "unreachable")

    assert caught.value.status_code == status_code
    assert caught.value.error_type == error_type
    assert caught.value.retryable is True


def test_model_connection_fault_is_distinct_from_tool_failure() -> None:
    executor = ModelCallExecutor(
        [(BeforeModelCall(1), ModelConnectionFault())]
    )

    with pytest.raises(ConnectionError, match="connection failure"):
        executor.execute(lambda: None)


def test_model_fault_failure_is_returned_as_scenario_execution_error() -> None:
    class ModelBackedAgent(Agent):
        def __init__(self) -> None:
            self.model_call_executor = ModelCallExecutor()

        def next_action(self, observation: Any) -> ToolCall | None:
            return self.model_call_executor.execute(lambda: None)

    scenario = Scenario(
        name="model times out",
        agent=ModelBackedAgent(),
        environment={},
        model_faults=[(BeforeModelCall(1), ModelTimeoutFault())],
    )

    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, TimeoutError)
    assert result.trajectory == []


def test_model_fault_requires_agent_to_expose_call_executor() -> None:
    class SimpleAgent(Agent):
        def next_action(self, observation: Any) -> ToolCall | None:
            return None

    scenario = Scenario(
        name="misconfigured model fault",
        agent=SimpleAgent(),
        environment={},
        model_faults=[(BeforeModelCall(1), ModelTimeoutFault())],
    )

    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, RuntimeError)
    assert "ModelCallExecutor" in str(result.error)
