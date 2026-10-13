"""Native LangChain v1 middleware for AgentFault scenarios.

Use this with langchain.agents.create_agent(..., middleware=[interceptor]).
Unlike the chat-model adapter, this integration observes the tool loop owned by
LangChain and injects faults at tool and model-call boundaries.
"""

from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
import json
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.faults import ModelCallExecutor
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.scenario import (
    FaultSchedule,
    ModelFaultSchedule,
    PerturbationSchedule,
    Scenario,
)
from agentfault.testing.scenario_result import ScenarioResult
from agentfault.tools import ToolCall
from agentfault.trajectory import TrajectoryStep


ToolCallHandler = Callable[[Any], Any]
AsyncToolCallHandler = Callable[[Any], Awaitable[Any]]


class LangChainToolCallInterceptor(AgentMiddleware[Any, Any, Any]):
    """AgentFault middleware for LangChain v1's native create_agent loop.

    The middleware implements LangChain's model and tool wrappers. It records
    completed tool executions, applies scenario perturbations at the same
    before/after boundaries as the generic runner, and sends recoverable tool
    faults back to the agent as error ToolMessages.

    Tool execution is supported in sync and async modes. Multiple tool calls
    returned in one model turn are rejected: a stateful perturbation must be
    visible to a fresh model decision before a consequential next action.
    Configure sequential tool calling where the provider supports it.
    """

    def __init__(
        self,
        environment: Any,
        perturbations: list[PerturbationSchedule] | None = None,
        faults: list[FaultSchedule] | None = None,
        model_faults: list[ModelFaultSchedule] | None = None,
        max_steps: int = 100,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.environment = environment
        self.perturbations = list(perturbations or [])
        self.faults = list(faults or [])
        self.max_steps = max_steps
        self.trajectory: list[TrajectoryStep] = []
        self.step_limit_reached = False
        self._pending_failures: list[ToolFailurePerturbation] = []
        self.model_call_executor = ModelCallExecutor(list(model_faults or []))

    def reset(self) -> None:
        """Clear tool evidence and queued failures before a new scenario run."""
        self.trajectory.clear()
        self._pending_failures.clear()
        self.step_limit_reached = False

    def wrap_tool_call(
        self,
        request: Any,
        handler: ToolCallHandler,
    ) -> Any:
        """Synchronously intercept one LangChain tool execution."""
        tool_call = self._to_tool_call(request)
        self._check_step_limit()
        self._apply_perturbations("before_tool", tool_call)

        pending_failure = self._take_pending_failure(tool_call)
        if pending_failure is not None:
            return self._tool_error(tool_call, RuntimeError(pending_failure.message))

        try:
            self._run_before_faults(tool_call)
            response = handler(request)
        except Exception as error:
            return self._tool_error(tool_call, error)

        return self._finish_tool_call(tool_call, response)

    async def awrap_tool_call(
        self,
        request: Any,
        handler: AsyncToolCallHandler,
    ) -> Any:
        """Asynchronously intercept one LangChain tool execution."""
        tool_call = self._to_tool_call(request)
        self._check_step_limit()
        self._apply_perturbations("before_tool", tool_call)

        pending_failure = self._take_pending_failure(tool_call)
        if pending_failure is not None:
            return self._tool_error(tool_call, RuntimeError(pending_failure.message))

        try:
            self._run_before_faults(tool_call)
            response = await handler(request)
        except Exception as error:
            return self._tool_error(tool_call, error)

        return self._finish_tool_call(tool_call, response)

    def wrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        """Intercept a LangChain model call and apply configured model faults."""
        response = self.model_call_executor.execute(lambda: handler(request))
        self._reject_parallel_tool_calls(response)
        return response

    async def awrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Asynchronous counterpart of wrap_model_call."""
        response = await self.model_call_executor.execute_async(
            lambda: handler(request)
        )
        self._reject_parallel_tool_calls(response)
        return response

    def _check_step_limit(self) -> None:
        if len(self.trajectory) >= self.max_steps:
            self.step_limit_reached = True
            raise RuntimeError(
                "LangChain exceeded the limit of "
                f"{self.max_steps} tool executions."
            )

    @staticmethod
    def _to_tool_call(request: Any) -> ToolCall:
        raw_call = getattr(request, "tool_call", None)
        if not isinstance(raw_call, Mapping):
            raise TypeError(
                "Expected a LangChain ToolCallRequest with a mapping tool_call."
            )

        name = raw_call.get("name")
        arguments = raw_call.get("args", raw_call.get("arguments", {}))
        call_id = raw_call.get("id")
        if not isinstance(name, str) or not name:
            raise ValueError("LangChain tool call is missing a tool name.")
        if not isinstance(arguments, Mapping):
            raise TypeError(f"Arguments for tool {name!r} must be a mapping.")
        if call_id is not None and not isinstance(call_id, str):
            raise TypeError("LangChain tool call id must be a string.")

        return ToolCall(name=name, arguments=dict(arguments), id=call_id)

    def _apply_perturbations(self, phase: str, tool_call: ToolCall) -> None:
        for trigger, perturbation in self.perturbations:
            if trigger.phase != phase or not trigger.matches(tool_call):
                continue
            if isinstance(perturbation, ToolFailurePerturbation):
                self._pending_failures.append(perturbation)
            else:
                perturbation.apply(self.environment)

    def _take_pending_failure(
        self,
        tool_call: ToolCall,
    ) -> ToolFailurePerturbation | None:
        for index, perturbation in enumerate(self._pending_failures):
            if perturbation.matches(tool_call):
                return self._pending_failures.pop(index)
        return None

    def _run_before_faults(self, tool_call: ToolCall) -> None:
        for trigger, fault in self.faults:
            if trigger.phase == "before_tool" and trigger.matches(tool_call):
                fault.before_execute(tool_call)

    def _finish_tool_call(self, tool_call: ToolCall, response: Any) -> Any:
        if getattr(response, "status", None) == "error":
            content = getattr(response, "content", "LangChain tool returned an error.")
            self._record_failure(
                tool_call,
                RuntimeError(str(content) or "LangChain tool returned an error."),
                observation=content,
            )
            return response

        has_matching_after_fault = any(
            trigger.phase == "after_tool" and trigger.matches(tool_call)
            for trigger, _ in self.faults
        )
        is_tool_message = isinstance(response, ToolMessage)
        if has_matching_after_fault and not is_tool_message:
            return self._tool_error(
                tool_call,
                TypeError(
                    "Response-transform faults require a LangChain ToolMessage; "
                    "tools returning Command objects cannot be transformed."
                ),
            )

        observed_response = getattr(response, "content", response)
        if has_matching_after_fault:
            try:
                observed_response = self._run_after_faults(
                    tool_call,
                    observed_response,
                )
            except Exception as error:
                return self._tool_error(tool_call, error)

            response = ToolMessage(
                content=self._serialize_tool_content(observed_response),
                tool_call_id=tool_call.id or getattr(response, "tool_call_id", ""),
                name=getattr(response, "name", tool_call.name),
                status=getattr(response, "status", "success"),
            )

        self.trajectory.append(
            TrajectoryStep(
                tool_call=tool_call,
                observation=deepcopy(observed_response),
            )
        )
        self._apply_perturbations("after_tool", tool_call)
        return response

    def _run_after_faults(self, tool_call: ToolCall, response: Any) -> Any:
        for trigger, fault in self.faults:
            if trigger.phase == "after_tool" and trigger.matches(tool_call):
                response = fault.after_execute(tool_call, response)
        return response

    def _tool_error(self, tool_call: ToolCall, error: Exception) -> ToolMessage:
        """Record a tool failure and make it observable to the agent for recovery."""
        self._record_failure(tool_call, error)
        return ToolMessage(
            content=str(error) or type(error).__name__,
            tool_call_id=tool_call.id or "",
            name=tool_call.name,
            status="error",
        )

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

    @staticmethod
    def _serialize_tool_content(value: Any) -> str | list[Any]:
        if isinstance(value, (str, list)):
            return value
        if value is None:
            return ""
        return json.dumps(value, default=str)

    @staticmethod
    def _reject_parallel_tool_calls(response: Any) -> None:
        """Enforce sequential stateful semantics when the model requests tools."""
        candidate = getattr(response, "result", response)
        tool_calls = getattr(candidate, "tool_calls", None) or []
        if len(tool_calls) > 1:
            raise RuntimeError(
                "AgentFault's native LangChain integration requires one tool call "
                "per model response. Configure the model for sequential tool calls."
            )


class LangChainScenarioRunner:
    """Run a compiled LangChain create_agent graph as an AgentFault scenario.

    Build the compiled agent with the same LangChainToolCallInterceptor in its
    middleware list, then place that graph in Scenario.agent. Sync invoke and
    async ainvoke are supported.
    """

    def __init__(
        self,
        scenario: Scenario,
        interceptor: LangChainToolCallInterceptor,
        max_steps: int = 100,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.scenario = scenario
        self.interceptor = interceptor
        self.max_steps = max_steps

    def _prepare(self) -> None:
        self.interceptor.environment = self.scenario.environment
        self.interceptor.perturbations = list(self.scenario.perturbations)
        self.interceptor.faults = list(self.scenario.faults)
        self.interceptor.max_steps = self.max_steps
        self.interceptor.model_call_executor.configure(self.scenario.model_faults)
        self.interceptor.reset()

    def run(self, inputs: Any, config: Any | None = None) -> ScenarioResult:
        """Run a synchronous native LangChain agent and evaluate assertions."""
        self._prepare()
        final_observation: Any = None
        terminal_error: Exception | None = None
        try:
            final_observation = self.scenario.agent.invoke(inputs, config=config)
        except Exception as error:
            terminal_error = error
        return self._evaluate(final_observation, terminal_error)

    async def arun(self, inputs: Any, config: Any | None = None) -> ScenarioResult:
        """Run an async native LangChain agent and evaluate assertions."""
        self._prepare()
        final_observation: Any = None
        terminal_error: Exception | None = None
        try:
            final_observation = await self.scenario.agent.ainvoke(inputs, config=config)
        except Exception as error:
            terminal_error = error
        return self._evaluate(final_observation, terminal_error)

    def _evaluate(
        self,
        final_observation: Any,
        terminal_error: Exception | None,
    ) -> ScenarioResult:
        if self.interceptor.step_limit_reached:
            terminal_error = RuntimeError(
                "LangChain reached the maximum of "
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
            result.passed for result in assertion_results
        )
        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=list(self.interceptor.trajectory),
            error=terminal_error,
        )
