from typing import Any

from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.faults import ToolFault
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.runner import AgentRunner
from agentfault.testing.scenario import FaultSchedule, Scenario
from agentfault.testing.scenario_result import ScenarioResult
from agentfault.testing.tools import Trigger
from agentfault.tools import (
    RegistryToolExecutor,
    ToolCall,
    ToolExecutionFailure,
    ToolExecutor,
    ToolRegistry,
)


class _PerturbableToolExecutor(ToolExecutor):
    def __init__(
        self,
        tool_executor: ToolExecutor,
        faults: list[FaultSchedule] | None = None,
    ) -> None:
        self.tool_executor = tool_executor
        self.faults = list(faults or [])
        self.pending_failures: list[ToolFailurePerturbation] = []

    def queue_failure(self, perturbation: ToolFailurePerturbation) -> None:
        self.pending_failures.append(perturbation)

    def execute(self, tool_call: ToolCall) -> Any:
        for trigger, fault in self.faults:
            if trigger.phase == "before_tool" and trigger.matches(tool_call):
                try:
                    fault.before_execute(tool_call)
                except Exception as error:
                    raise ToolExecutionFailure(tool_call.name, error) from error

        for index, perturbation in enumerate(self.pending_failures):
            if perturbation.matches(tool_call):
                del self.pending_failures[index]
                try:
                    perturbation.apply(None)
                except Exception as error:
                    raise ToolExecutionFailure(tool_call.name, error) from error

        response = self.tool_executor.execute(tool_call)

        for trigger, fault in self.faults:
            if trigger.phase == "after_tool" and trigger.matches(tool_call):
                try:
                    response = fault.after_execute(tool_call, response)
                except Exception as error:
                    raise ToolExecutionFailure(tool_call.name, error) from error

        return response


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry, max_steps: int = 100) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def run(self, scenario: Scenario) -> ScenarioResult:
        tool_executor = _PerturbableToolExecutor(
            RegistryToolExecutor(self.tool_registry),
            faults=scenario.faults,
        )

        def apply_matching_perturbations(
            phase: str, tool_call: ToolCall
        ) -> None:
            for trigger, perturbation in scenario.perturbations:
                if trigger.phase == phase and trigger.matches(tool_call):
                    if isinstance(perturbation, ToolFailurePerturbation):
                        tool_executor.queue_failure(perturbation)
                    else:
                        perturbation.apply(scenario.environment)

        def before_tool_execution(tool_call: ToolCall) -> None:
            apply_matching_perturbations("before_tool", tool_call)

        def on_tool_executed(tool_call: ToolCall, _: Any) -> None:
            apply_matching_perturbations("after_tool", tool_call)

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
