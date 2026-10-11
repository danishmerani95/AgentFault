from typing import Any

from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkCase, BenchmarkRunner, BenchmarkSuite
from agentfault.testing import Scenario, ScenarioRunner
from agentfault.tools import ToolCall, ToolRegistry


class NoOpAgent(Agent):
    def next_action(self, observation: Any) -> ToolCall | None:
        return None


def build_case(agent_factory: Any) -> tuple[Scenario, ToolRegistry]:
    return (
        Scenario(
            name="custom executor case",
            agent=agent_factory("no tools", []),
            environment={},
        ),
        ToolRegistry([]),
    )


def test_benchmark_accepts_a_pluggable_scenario_executor() -> None:
    suite = BenchmarkSuite(
        id="custom-executor",
        version="1.0.0",
        category="testing",
        description="Verifies framework-owned scenario execution can be plugged in.",
        cases=(BenchmarkCase("EXT-001", "Custom executor", build_case),),
    )
    calls: list[tuple[str, int]] = []

    def executor(scenario: Scenario, registry: ToolRegistry, max_steps: int):
        calls.append((scenario.name, max_steps))
        return ScenarioRunner(registry, max_steps=max_steps).run(scenario)

    result = BenchmarkRunner(max_steps=7).run(
        suite,
        lambda task, tools: NoOpAgent(),
        scenario_executor=executor,
    )

    assert calls == [("custom executor case", 7)]
    assert result.complete
    assert result.score == 100.0
