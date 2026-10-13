from typing import Any

import pytest

from agentfault.agent import Agent
from agentfault.benchmarks import (
    BenchmarkCase,
    BenchmarkRunner,
    BenchmarkSuite,
)
from agentfault.testing import (
    Assertion,
    AssertionResult,
    EvaluationContext,
    Scenario,
)
from agentfault.tools import ToolCall, ToolRegistry


class NoOpAgent(Agent):
    def next_action(self, observation: Any) -> ToolCall | None:
        return None


class FailingAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        return AssertionResult(passed=False, message="Expected test failure.")


def build_case(agent_factory: Any) -> tuple[Scenario, ToolRegistry]:
    tools = ToolRegistry([])
    agent = agent_factory("do nothing", [])
    return Scenario(
        name="no-op",
        agent=agent,
        environment={},
        assertions=[],
    ), tools


def build_failing_case(agent_factory: Any) -> tuple[Scenario, ToolRegistry]:
    scenario, tools = build_case(agent_factory)
    scenario.assertions.append(FailingAssertion())
    return scenario, tools


def make_suite() -> BenchmarkSuite:
    return BenchmarkSuite(
        id="test-suite",
        version="1.0.0",
        category="testing",
        description="Exercise the generic benchmark runner.",
        cases=(
            BenchmarkCase("pass", "No-op passes", build_case),
            BenchmarkCase("fail", "Assertion fails", build_failing_case),
        ),
    )


def test_benchmark_runner_aggregates_case_results() -> None:
    result = BenchmarkRunner().run(
        make_suite(),
        agent_factory=lambda task, tools: NoOpAgent(),
    )

    assert [case.status for case in result.cases] == ["passed", "failed"]
    assert result.complete is True
    assert result.score == 50.0
    assert result.passed_count == 1
    assert result.failed_count == 1
    assert result.error_count == 0


def test_case_factory_error_makes_headline_score_unavailable() -> None:
    def broken_factory(agent_factory: Any) -> tuple[Scenario, ToolRegistry]:
        raise RuntimeError("fixture failed")

    suite = BenchmarkSuite(
        id="broken-suite",
        version="1.0.0",
        category="testing",
        description="A suite with a broken fixture.",
        cases=(BenchmarkCase("broken", "Broken setup", broken_factory),),
    )
    result = BenchmarkRunner().run(
        suite,
        agent_factory=lambda task, tools: NoOpAgent(),
    )

    assert result.cases[0].status == "error"
    assert result.complete is False
    assert result.score is None
    assert result.error_count == 1
    assert result.to_dict()["score"] is None


def test_suite_requires_unique_case_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        BenchmarkSuite(
            id="duplicate-suite",
            version="1.0.0",
            category="testing",
            description="Duplicate ids are invalid.",
            cases=(
                BenchmarkCase("same", "First", build_case),
                BenchmarkCase("same", "Second", build_case),
            ),
        )


def test_runner_rejects_invalid_step_limit() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        BenchmarkRunner(max_steps=0)

def test_benchmark_json_includes_each_scenarios_event_timeline() -> None:
    result = BenchmarkRunner().run(
        make_suite(),
        agent_factory=lambda task, tools: NoOpAgent(),
    )

    first_case = result.to_dict()["cases"][0]
    events = first_case["events"]

    assert events
    assert events[0]["kind"] == "scenario"
    assert events[0]["outcome"] == "started"
    assert events[-1]["kind"] == "scenario"
    assert events[-1]["outcome"] == "passed"
    assert events[0]["run_id"] == events[-1]["run_id"]
