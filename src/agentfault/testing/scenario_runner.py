from typing import Any

from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.runner import AgentRunner
from agentfault.testing.scenario import Scenario
from agentfault.testing.scenario_result import ScenarioResult
from agentfault.testing.triggers import AfterTool, BeforeTool, Trigger
from agentfault.tools import (
    RegistryToolExecutor,
    ToolCall,
    ToolExecutionFailure,
    ToolExecutor,
    ToolRegistry,
)


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
                try:
                    perturbation.apply(None)
                except Exception as error:
                    raise ToolExecutionFailure(tool_call.name, error) from error

        return self.tool_executor.execute(tool_call)


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry, max_steps: int = 100) -> None:
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def run(self, scenario: Scenario) -> ScenarioResult:
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

        agent_runner = AgentRunner(
            agent=scenario.agent,
            tool_executor=tool_executor,
            before_tool_execution=before_tool_execution,
            on_tool_executed=on_tool_executed,
            max_steps=self.max_steps,
        )
        final_observation = agent_runner.run()
        terminal_error = None
        if agent_runner.step_limit_reached:
            terminal_error = RuntimeError(
                "AgentRunner reached its maximum of "
                f"{agent_runner.max_steps} tool executions before the agent stopped."
            )

        evaluation_context = EvaluationContext(
            final_observation=final_observation,
            trajectory=agent_runner.trajectory,
            error=terminal_error,
            environment=scenario.environment,
        )

        assertion_results: list[AssertionResult] = [
            assertion.check(evaluation_context)
            for assertion in scenario.assertions
        ]
        passed = terminal_error is None and all(
            assertion_result.passed for assertion_result in assertion_results
        )

        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=agent_runner.trajectory,
            error=terminal_error,
        )
