"""LangGraph ToolNode integration for stateful AgentFault scenarios.

This module intentionally avoids importing LangGraph at import time. Install a
compatible LangGraph release in applications that use this integration.
"""

from collections.abc import Callable, Mapping
from typing import Any

from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.perturbations import (
    Perturbation,
    ToolFailurePerturbation,
)
from agentfault.testing.scenario import Scenario
from agentfault.testing.scenario_result import ScenarioResult
from agentfault.testing.triggers import AfterTool, BeforeTool, Trigger
from agentfault.tools import ToolCall, ToolExecutionFailure
from agentfault.trajectory import TrajectoryStep


ToolCallHandler = Callable[[Any], Any]
PerturbationSchedule = tuple[Trigger, Perturbation]


class LangGraphToolCallInterceptor:
    """Callable for LangGraph's ToolNode wrap_tool_call hook.

    The interceptor records each tool execution, applies scenario perturbations
    immediately before/after the matching execution, and keeps a trajectory for
    AgentFault assertions. It is designed for sequential, synchronous tool calls.
    """

    def __init__(
        self,
        environment: Any,
        perturbations: list[PerturbationSchedule],
        max_steps: int = 100,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.environment = environment
        self.perturbations = perturbations
        self.max_steps = max_steps
        self.trajectory: list[TrajectoryStep] = []
        self.step_limit_reached = False
        self._pending_failures: list[ToolFailurePerturbation] = []

    def reset(self) -> None:
        """Clear execution evidence before a new invocation."""
        self.trajectory.clear()
        self._pending_failures.clear()
        self.step_limit_reached = False

    def __call__(self, request: Any, handler: ToolCallHandler) -> Any:
        """Intercept one LangGraph ToolNode call without changing its response."""
        tool_call = self._to_tool_call(request)

        if len(self.trajectory) >= self.max_steps:
            self.step_limit_reached = True
            raise RuntimeError(
                f"LangGraph exceeded the limit of {self.max_steps} tool executions."
            )

        self._apply_matching_perturbations(BeforeTool, tool_call)

        pending_failure = self._take_pending_failure(tool_call)
        if pending_failure is not None:
            error = RuntimeError(pending_failure.message)
            self._record_failure(tool_call, error)
            raise ToolExecutionFailure(tool_call.name, error) from error

        try:
            response = handler(request)
        except Exception as error:
            self._record_failure(tool_call, error)
            raise

        if getattr(response, "status", None) == "error":
            message = getattr(response, "content", "LangGraph tool returned an error.")
            self._record_failure(
                tool_call,
                RuntimeError(str(message) or "LangGraph tool returned an error."),
                observation=message,
            )
            return response

        self.trajectory.append(
            TrajectoryStep(
                tool_call=tool_call,
                observation=getattr(response, "content", response),
            )
        )
        self._apply_matching_perturbations(AfterTool, tool_call)
        return response

    @staticmethod
    def _to_tool_call(request: Any) -> ToolCall:
        raw_call = getattr(request, "tool_call", None)
        if not isinstance(raw_call, Mapping):
            raise TypeError(
                "Expected LangGraph ToolCallRequest with a mapping tool_call."
            )

        name = raw_call.get("name")
        arguments = raw_call.get("args", raw_call.get("arguments", {}))
        call_id = raw_call.get("id")

        if not isinstance(name, str) or not name:
            raise ValueError("LangGraph tool call is missing a tool name.")
        if not isinstance(arguments, Mapping):
            raise TypeError(f"Arguments for tool {name!r} must be a mapping.")

        return ToolCall(
            name=name,
            arguments=dict(arguments),
            id=call_id if isinstance(call_id, str) else None,
        )

    def _apply_matching_perturbations(
        self, trigger_type: type[Trigger], tool_call: ToolCall
    ) -> None:
        for trigger, perturbation in self.perturbations:
            if not isinstance(trigger, trigger_type) or not trigger.matches(tool_call):
                continue

            if isinstance(perturbation, ToolFailurePerturbation):
                self._pending_failures.append(perturbation)
            else:
                perturbation.apply(self.environment)

    def _take_pending_failure(
        self, tool_call: ToolCall
    ) -> ToolFailurePerturbation | None:
        for index, perturbation in enumerate(self._pending_failures):
            if perturbation.matches(tool_call):
                return self._pending_failures.pop(index)
        return None

    def _record_failure(
        self,
        tool_call: ToolCall,
        error: Exception,
        observation: Any | None = None,
    ) -> None:
        error_type = type(error).__name__
        message = str(error) or error_type
        failure_observation = observation
        if failure_observation is None:
            failure_observation = {
                "type": "tool_error",
                "tool_name": tool_call.name,
                "error_type": error_type,
                "message": message,
            }

        self.trajectory.append(
            TrajectoryStep(
                tool_call=tool_call,
                observation=failure_observation,
                error={"type": error_type, "message": message},
            )
        )


class LangGraphScenarioRunner:
    """Run a compiled LangGraph using a configured AgentFault tool interceptor.

    The graph must have been built with the same interceptor passed here, e.g.
    ToolNode(tools, wrap_tool_call=interceptor).
    """

    def __init__(
        self,
        scenario: Scenario,
        interceptor: LangGraphToolCallInterceptor,
    ) -> None:
        self.scenario = scenario
        self.interceptor = interceptor

    def run(self, inputs: Any, config: Any | None = None) -> ScenarioResult:
        """Invoke the graph and evaluate the scenario's normal assertions."""
        self.interceptor.reset()
        final_observation: Any = None
        terminal_error: Exception | None = None

        try:
            final_observation = self.scenario.agent.invoke(inputs, config=config)
        except Exception as error:
            terminal_error = error

        if self.interceptor.step_limit_reached:
            terminal_error = RuntimeError(
                f"LangGraph reached the maximum of "
                f"{self.interceptor.max_steps} tool executions."
            )

        context = EvaluationContext(
            final_observation=final_observation,
            trajectory=self.interceptor.trajectory,
            error=terminal_error,
            environment=self.scenario.environment,
        )
        assertion_results: list[AssertionResult] = [
            assertion.check(context) for assertion in self.scenario.assertions
        ]
        passed = terminal_error is None and all(
            assertion_result.passed for assertion_result in assertion_results
        )

        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=list(self.interceptor.trajectory),
            error=terminal_error,
        )
