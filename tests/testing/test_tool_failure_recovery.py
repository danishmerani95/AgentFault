from typing import Any

import pytest

from agentfault.agent import Agent
from agentfault.testing import Scenario, ScenarioRunner
from agentfault.testing.runner import AgentRunner
from agentfault.tools import (
    Tool,
    ToolCall,
    ToolExecutionFailure,
    ToolExecutor,
    ToolRegistry,
)


class _RecoveryAgent(Agent):
    def __init__(self, *, retry: bool) -> None:
        self.retry = retry
        self.observations: list[Any] = []

    def next_action(self, observation: Any) -> ToolCall | None:
        self.observations.append(observation)
        if len(self.observations) == 1:
            return ToolCall(name="unstable_tool", arguments={})
        if isinstance(observation, dict) and observation.get("type") == "tool_error":
            if self.retry:
                return ToolCall(name="unstable_tool", arguments={})
            return None
        return None


class _FailOnceExecutor(ToolExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, tool_call: ToolCall) -> str:
        self.calls += 1
        if self.calls == 1:
            raise ToolExecutionFailure(
                tool_call.name, RuntimeError("temporary failure")
            )
        return "recovered"


class _AlwaysFailExecutor(ToolExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, tool_call: ToolCall) -> Any:
        self.calls += 1
        raise ToolExecutionFailure(
            tool_call.name, RuntimeError("still failing")
        )


class _AlwaysRetryAgent(Agent):
    def __init__(self) -> None:
        self.calls = 0

    def next_action(self, observation: Any) -> ToolCall:
        self.calls += 1
        return ToolCall(name="unstable_tool", arguments={})


def test_agent_recovers_after_tool_error_feedback() -> None:
    agent = _RecoveryAgent(retry=True)
    executor = _FailOnceExecutor()
    runner = AgentRunner(agent=agent, tool_executor=executor, max_steps=5)

    result = runner.run()

    assert result == "recovered"
    assert executor.calls == 2
    assert agent.observations[1] == {
        "type": "tool_error",
        "tool_name": "unstable_tool",
        "error_type": "RuntimeError",
        "message": "temporary failure",
    }
    assert len(runner.trajectory) == 2
    assert runner.trajectory[0].succeeded is False
    assert runner.trajectory[1].succeeded is True
    assert runner.step_limit_reached is False


def test_agent_can_stop_after_tool_error_feedback() -> None:
    agent = _RecoveryAgent(retry=False)
    executor = _AlwaysFailExecutor()
    runner = AgentRunner(agent=agent, tool_executor=executor, max_steps=5)

    result = runner.run()

    assert result == {
        "type": "tool_error",
        "tool_name": "unstable_tool",
        "error_type": "RuntimeError",
        "message": "still failing",
    }
    assert executor.calls == 1
    assert len(runner.trajectory) == 1
    assert runner.step_limit_reached is False


def test_repeated_failures_are_bounded_by_max_steps() -> None:
    agent = _AlwaysRetryAgent()
    executor = _AlwaysFailExecutor()
    runner = AgentRunner(agent=agent, tool_executor=executor, max_steps=3)

    runner.run()

    assert executor.calls == 3
    assert agent.calls == 3
    assert len(runner.trajectory) == 3
    assert runner.step_limit_reached is True


def test_agent_decision_errors_are_not_misclassified_as_tool_errors() -> None:
    class _BrokenAgent(Agent):
        def next_action(self, observation: Any) -> ToolCall:
            raise RuntimeError("agent decision failed")

    executor = _AlwaysFailExecutor()
    runner = AgentRunner(agent=_BrokenAgent(), tool_executor=executor)

    with pytest.raises(RuntimeError, match="agent decision failed"):
        runner.run()

    assert executor.calls == 0
    assert runner.trajectory == []


def test_scenario_runner_fails_if_agent_never_stops() -> None:
    agent = _AlwaysRetryAgent()
    registry = ToolRegistry(
        [Tool(name="unstable_tool", description="successful tool", function=lambda: "ok")]
    )
    scenario = Scenario(name="bounded run", agent=agent, environment={}, assertions=[])

    result = ScenarioRunner(registry, max_steps=3).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, RuntimeError)
    assert "maximum of 3 tool executions" in str(result.error)
    assert len(result.trajectory) == 3



def test_unknown_tool_errors_abort_instead_of_becoming_tool_feedback() -> None:
    class _UnknownToolAgent(Agent):
        def __init__(self) -> None:
            self.calls = 0

        def next_action(self, observation: Any) -> ToolCall | None:
            self.calls += 1
            return ToolCall(name="not_registered", arguments={})

    agent = _UnknownToolAgent()
    runner = AgentRunner(agent=agent, tool_registry=ToolRegistry([]))

    with pytest.raises(ValueError, match="Unknown tool"):
        runner.run()

    assert agent.calls == 1
    assert runner.trajectory == []
