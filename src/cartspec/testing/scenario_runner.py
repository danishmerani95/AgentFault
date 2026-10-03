from typing import Any

from cartspec.testing.assertion import AssertionResult
from cartspec.testing.perturbations.base import Perturbation
from cartspec.testing.runner import AgentRunner
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_result import ScenarioResult
from cartspec.testing.triggers.tool import ToolTrigger
from cartspec.tools.tool import ToolCall, ToolRegistry


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def run(self, scenario: Scenario) -> ScenarioResult:
        pending_perturbations: list[Perturbation] = []
        execution_error: Exception | None = None

        def before_tool_execution(_: ToolCall) -> None:
            for perturbation in pending_perturbations:
                perturbation.apply(scenario.environment)
            pending_perturbations.clear()

        def on_tool_executed(tool_call: ToolCall, _: Any) -> None:
            for trigger in scenario.perturbations:
                if isinstance(trigger, ToolTrigger) and trigger.tool_name == tool_call.name:
                    pending_perturbations.append(trigger.perturbation)

        def on_tool_error(_: ToolCall, error: Exception) -> None:
            nonlocal execution_error
            execution_error = error

        agent_runner = AgentRunner(
            agent=scenario.agent,
            tool_registry=self.tool_registry,
            before_tool_execution=before_tool_execution,
            on_tool_executed=on_tool_executed,
            on_tool_error=on_tool_error,
        )
        result = agent_runner.run()

        assertion_results: list[AssertionResult] = [
            assertion.check(result=result, trajectory=agent_runner.trajectory)
            for assertion in scenario.assertions
        ]
        passed = execution_error is None and all(
            assertion_result.passed for assertion_result in assertion_results
        )

        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=agent_runner.trajectory,
            error=execution_error,
        )
