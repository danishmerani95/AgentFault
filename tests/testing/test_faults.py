from typing import Any

import pytest

from agentfault.agent import Agent
from agentfault.testing import (
    EmptyResponseFault,
    LatencyFault,
    MalformedResponseFault,
    Scenario,
    ScenarioRunner,
    ToolTimeoutFault,
    TransientToolFailureFault,
    TruncatedResponseFault,
)
from agentfault.testing.triggers import AfterTool, BeforeTool, Trigger
from agentfault.tools import Tool, ToolCall, ToolRegistry


class SingleToolAgent(Agent):
    def __init__(self, tool_name: str, calls: int = 1) -> None:
        self.tool_name = tool_name
        self.remaining = calls

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.remaining < 1:
            return None
        self.remaining -= 1
        return ToolCall(self.tool_name, {})


def build_scenario(
    *,
    result: Any = "complete response",
    fault: Any,
    trigger: Trigger,
    calls: int = 1,
) -> tuple[Scenario, dict[str, int]]:
    executions = {"count": 0}

    def fetch() -> Any:
        executions["count"] += 1
        return result

    registry = ToolRegistry(
        [Tool(name="fetch", description="Return a test response.", function=fetch)]
    )
    scenario = Scenario(
        name="fault injection unit test",
        agent=SingleToolAgent("fetch", calls=calls),
        environment={},
        faults=[(trigger, fault)],
    )
    return scenario, executions, registry


def test_timeout_fault_is_recorded_and_skips_real_tool() -> None:
    scenario, executions, registry = build_scenario(
        fault=ToolTimeoutFault(),
        trigger=BeforeTool("fetch"),
    )

    result = ScenarioRunner(registry).run(scenario)

    assert executions["count"] == 0
    assert len(result.trajectory) == 1
    assert result.trajectory[0].succeeded is False
    assert result.trajectory[0].error == {
        "type": "TimeoutError",
        "message": "Injected tool timeout.",
    }


def test_malformed_response_reaches_agent_as_a_successful_but_corrupted_result() -> None:
    scenario, executions, registry = build_scenario(
        fault=MalformedResponseFault("{not-valid-json"),
        trigger=AfterTool("fetch"),
    )

    result = ScenarioRunner(registry).run(scenario)

    assert executions["count"] == 1
    assert result.trajectory[0].succeeded is True
    assert result.trajectory[0].observation == "{not-valid-json"


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("abcdef", "abc"),
        (b"abcdef", b"abc"),
        ([1, 2, 3, 4], [1, 2, 3]),
        ((1, 2, 3, 4), (1, 2, 3)),
    ],
)
def test_truncated_response_fault_supports_common_response_types(
    original: Any, expected: Any
) -> None:
    scenario, _, registry = build_scenario(
        result=original,
        fault=TruncatedResponseFault(3),
        trigger=AfterTool("fetch"),
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.trajectory[0].observation == expected


def test_empty_response_fault_returns_none_without_marking_tool_failed() -> None:
    scenario, _, registry = build_scenario(
        result={"status": "ok"},
        fault=EmptyResponseFault(),
        trigger=AfterTool("fetch"),
    )

    result = ScenarioRunner(registry).run(scenario)

    assert result.trajectory[0].succeeded is True
    assert result.trajectory[0].observation is None


def test_latency_fault_uses_injected_sleeper_at_trigger_phase() -> None:
    sleeps: list[float] = []
    scenario, _, registry = build_scenario(
        fault=LatencyFault(0.25, sleeper=sleeps.append),
        trigger=AfterTool("fetch"),
    )

    result = ScenarioRunner(registry).run(scenario)

    assert sleeps == [0.25]
    assert result.trajectory[0].observation == "complete response"


def test_transient_fault_fails_configured_number_of_calls_then_recovers() -> None:
    scenario, executions, registry = build_scenario(
        fault=TransientToolFailureFault(failures=1),
        trigger=BeforeTool("fetch"),
        calls=2,
    )

    result = ScenarioRunner(registry).run(scenario)

    assert executions["count"] == 1
    assert [step.succeeded for step in result.trajectory] == [False, True]
    assert result.trajectory[0].error is not None
    assert result.trajectory[1].observation == "complete response"


@pytest.mark.parametrize(
    ("constructor", "kwargs"),
    [
        (TruncatedResponseFault, {"max_length": -1}),
        (LatencyFault, {"delay_seconds": -0.1}),
        (TransientToolFailureFault, {"failures": 0}),
    ],
)
def test_faults_reject_invalid_configuration(
    constructor: Any, kwargs: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        constructor(**kwargs)
