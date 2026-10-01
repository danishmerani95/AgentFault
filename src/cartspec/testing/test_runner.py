from typing import Any

from cartspec.testing.assertion import AssertionResult
from cartspec.testing.perturbations.base import Perturbation
from cartspec.testing.runner import AgentRunner
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_result import ScenarioResult
from cartspec.tools.tool import ToolCall, ToolRegistry


class TestRunner:
    __test__ = False

    def __init__(
        self,
        tool_registry: ToolRegistry,
    ) -> None:
        self.tool_registry = tool_registry
        self.pending_perturbations: list[Perturbation] = []
        self.execution_error: Exception | None = None

    def run(self, scenario: Scenario) -> ScenarioResult:
        agent_runner = AgentRunner(
            agent=scenario.agent,
            tool_registry=self.tool_registry,
            before_tool_execution=lambda tool_call: self._before_tool_executed(
                scenario.environment, tool_call
            ),
            on_tool_executed=lambda tool_call, _: self._on_tool_executed(
                scenario, tool_call
            ),
            on_tool_error=self._on_tool_error,
        )

        result = agent_runner.run()

        assertion_results: list[AssertionResult] = [
            assertion.check(
                result=result,
                trajectory=agent_runner.trajectory,
            )
            for assertion in scenario.assertions
        ]

        passed = self.execution_error is None and all(
            assertion_result.passed for assertion_result in assertion_results
        )

        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=agent_runner.trajectory,
            error=self.execution_error,
        )

    def _before_tool_executed(self, environment: Any, _: ToolCall) -> None:
        for perturbation in self.pending_perturbations:
            perturbation.apply(environment)

        self.pending_perturbations = []

    def _on_tool_executed(self, scenario: Scenario, tool_call: ToolCall) -> None:
        for trigger in scenario.perturbations:
            if trigger.tool_name == tool_call.name:
                self.pending_perturbations.append(trigger.perturbation)

    def _on_tool_error(self, tool_call: ToolCall, error: Exception) -> None:
        self.execution_error = error
