from typing import Any

import pytest

from agentfault.agent import Agent
from agentfault.benchmarks import (
    BenchmarkCase,
    BenchmarkSuite,
    RepeatedBenchmarkRunner,
)
from agentfault.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from agentfault.tools import Tool, ToolCall, ToolRegistry


class ActionAgent(Agent):
    def __init__(self, should_act: bool) -> None:
        self.should_act = should_act
        self.acted = False

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.should_act and not self.acted:
            self.acted = True
            return ToolCall("act", {})
        return None


class ActionRequiredAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        passed = bool(context.environment["acted"])
        return AssertionResult(passed, "action was executed" if passed else "action missing")


def build_case(agent_factory: Any) -> tuple[Scenario, ToolRegistry]:
    environment = {"acted": False}

    def act() -> str:
        environment["acted"] = True
        return "done"

    tools = [
        Tool(name="act", description="Perform the required action.", function=act)
    ]
    agent = agent_factory("action-required task", tools)
    scenario = Scenario(
        name="require action",
        agent=agent,
        environment=environment,
        assertions=[ActionRequiredAssertion()],
    )
    return scenario, ToolRegistry(tools)


def make_suite() -> BenchmarkSuite:
    return BenchmarkSuite(
        id="repeat-test-suite",
        version="1.0.0",
        category="testing",
        description="Verify repeat-run statistics.",
        cases=(BenchmarkCase("ACT-001", "Action must occur", build_case),),
    )


def test_repeated_runner_computes_pass_rate_pass_k_mean_and_stddev() -> None:
    factory_calls = 0

    def flaky_factory(task: str, tools: list[Tool]) -> Agent:
        nonlocal factory_calls
        factory_calls += 1
        return ActionAgent(should_act=factory_calls % 2 == 1)

    result = RepeatedBenchmarkRunner().run(
        make_suite(),
        flaky_factory,
        repetitions=4,
        agent_name="fixture-agent",
    )

    assert result.repetitions == 4
    assert result.complete is True
    assert result.per_case_pass_rate == {"ACT-001": 0.5}
    assert result.pass_k == 0.0
    assert result.score_mean == 50.0
    assert result.score_stddev == 50.0
    payload = result.to_dict()
    assert payload["repetitions"] == 4
    assert payload["per_case_pass_rate"] == {"ACT-001": 0.5}


def test_any_invalid_repetition_withholds_mean_and_stddev_but_keeps_error_count() -> None:
    calls = 0

    def sometimes_broken_factory(task: str, tools: list[Tool]) -> Agent:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("provider unavailable")
        return ActionAgent(should_act=True)

    result = RepeatedBenchmarkRunner().run(
        make_suite(),
        sometimes_broken_factory,
        repetitions=3,
    )

    assert result.complete is False
    assert result.score_mean is None
    assert result.score_stddev is None
    assert result.error_count == 1
    assert result.per_case_pass_rate == {"ACT-001": 2 / 3}
    assert result.pass_k == 0.0


def test_repeated_runner_rejects_zero_repetitions() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        RepeatedBenchmarkRunner().run(
            make_suite(),
            lambda task, tools: ActionAgent(should_act=True),
            repetitions=0,
        )
