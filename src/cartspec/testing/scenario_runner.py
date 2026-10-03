from typing import Any

from cartspec.testing.assertion import AssertionResult, EvaluationContext
from cartspec.testing.runner import AgentRunner
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_result import ScenarioResult
from cartspec.testing.triggers import AfterTool, BeforeTool, Trigger
from cartspec.tools.tool import ToolCall, ToolRegistry


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def run(self, scenario: Scenario) -> ScenarioResult:
        execution_error: Exception | None = None

        def apply_matching_perturbations(
            trigger_type: type[Trigger], tool_call: ToolCall
        ) -> None:
            for trigger, perturbation in scenario.perturbations:
                if isinstance(trigger, trigger_type) and trigger.matches(tool_call):
                    perturbation.apply(scenario.environment)

        def before_tool_execution(tool_call: ToolCall) -> None:
            apply_matching_perturbations(BeforeTool, tool_call)

        def on_tool_executed(tool_call: ToolCall, _: Any) -> None:
            apply_matching_perturbations(AfterTool, tool_call)

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
        evaluation_context = EvaluationContext(
            final_observation=result,
            trajectory=agent_runner.trajectory,
            error=execution_error,
            environment=scenario.environment,
        )

        assertion_results: list[AssertionResult] = [
            assertion.check(evaluation_context)
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
