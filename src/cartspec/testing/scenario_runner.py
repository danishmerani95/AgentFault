from typing import Any

from cartspec.testing.assertion import AssertionResult, EvaluationContext
from cartspec.testing.perturbations import ToolFailurePerturbation
from cartspec.testing.runner import AgentRunner
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_result import ScenarioResult
from cartspec.testing.triggers import AfterTool, BeforeTool, Trigger
from cartspec.tools import RegistryToolExecutor, ToolCall, ToolExecutor, ToolRegistry


class _PerturbableToolExecutor(ToolExecutor):
    def __init__(self, tool_executor: ToolExecutor) -> None:
        self.tool_executor = tool_executor
        self.pending_failures: list[ToolFailurePerturbation] = []

    def queue_failure(self, perturbation: ToolFailurePerturbation) -> None:
        self.pending_failures.append(perturbation)

    def execute(self, tool_call: ToolCall) -> Any:
        for index, perturbation in enumerate(self.pending_failures):
            if perturbation.matches(tool_call):
                del self.pending_failures[index]
                perturbation.apply(None)

        return self.tool_executor.execute(tool_call)


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def run(self, scenario: Scenario) -> ScenarioResult:
        execution_error: Exception | None = None
        tool_executor = _PerturbableToolExecutor(RegistryToolExecutor(self.tool_registry))

        def apply_matching_perturbations(
            trigger_type: type[Trigger], tool_call: ToolCall
        ) -> None:
            for trigger, perturbation in scenario.perturbations:
                if isinstance(trigger, trigger_type) and trigger.matches(tool_call):
                    if isinstance(perturbation, ToolFailurePerturbation):
                        tool_executor.queue_failure(perturbation)
                    else:
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
            tool_executor=tool_executor,
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
