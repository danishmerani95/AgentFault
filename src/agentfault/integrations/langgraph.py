"""Synchronous and asynchronous LangGraph integration for AgentFault.

This module avoids importing LangGraph at import time. Pass both
wrap_tool_call=interceptor and awrap_tool_call=interceptor.awrap_tool_call
to ToolNode to cover sync and async graph execution. Model nodes should call
interceptor.invoke_model(...) or await interceptor.ainvoke_model(...) so
scheduled model faults and model timing are observed at the real call boundary.
"""

from collections.abc import Awaitable, Callable, Mapping
from importlib import import_module
import json
from typing import Any

from agentfault.observability import TraceRecorder
from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.faults import ModelCallExecutor
from agentfault.testing.perturbations import Perturbation, ToolFailurePerturbation
from agentfault.testing.scenario import FaultSchedule, Scenario
from agentfault.testing.scenario_result import ScenarioResult
from agentfault.testing.triggers import AfterTool, BeforeTool, Trigger
from agentfault.tools import ToolCall
from agentfault.trajectory import TrajectoryStep


ToolCallHandler = Callable[[Any], Any]
AsyncToolCallHandler = Callable[[Any], Awaitable[Any]]
PerturbationSchedule = tuple[Trigger, Perturbation]


class LangGraphToolCallInterceptor:
    """Callable sync/async wrappers for LangGraph's ToolNode execution hooks.

    Tool execution is intercepted one request at a time. The model-call helpers
    reject responses with multiple tool calls when stateful perturbations are in
    use; a single model decision cannot safely depend on another tool in the same
    batch having already changed the environment.
    """

    def __init__(
        self,
        environment: Any,
        perturbations: list[PerturbationSchedule] | None = None,
        max_steps: int = 100,
        faults: list[FaultSchedule] | None = None,
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
        self.trace = TraceRecorder()
        self.model_call_executor = ModelCallExecutor(trace=self.trace)

    def reset(self) -> None:
        """Clear tool evidence and queued failures before a new invocation."""
        self.trajectory.clear()
        self._pending_failures.clear()
        self.step_limit_reached = False

    def invoke_model(self, call: Callable[[], Any]) -> Any:
        """Invoke one model call with the scenario's scheduled model faults."""
        response = self.model_call_executor.execute(call)
        self._reject_parallel_tool_calls(response)
        return response

    async def ainvoke_model(self, call: Callable[[], Awaitable[Any]]) -> Any:
        """Asynchronously invoke a model call with scheduled model faults."""
        response = await self.model_call_executor.execute_async(call)
        self._reject_parallel_tool_calls(response)
        return response

    def __call__(self, request: Any, handler: ToolCallHandler) -> Any:
        """Intercept one synchronous LangGraph ToolNode call."""
        tool_call = self._to_tool_call(request)
        self._check_step_limit(tool_call)
        started = self._record_tool_start(tool_call)
        self._apply_matching_perturbations(BeforeTool, tool_call)

        pending_failure = self._take_pending_failure(tool_call)
        if pending_failure is not None:
            response = self._tool_error(tool_call, RuntimeError(pending_failure.message))
            self._record_tool_end(tool_call, response, started)
            return response

        try:
            self._run_before_faults(tool_call)
            response = handler(request)
        except Exception as error:
            response = self._tool_error(tool_call, error)
            self._record_tool_end(tool_call, response, started)
            return response

        response = self._finish_tool_call(tool_call, response)
        self._record_tool_end(tool_call, response, started)
        if getattr(response, "status", None) != "error":
            self._apply_matching_perturbations(AfterTool, tool_call)
        return response

    async def awrap_tool_call(
        self,
        request: Any,
        handler: AsyncToolCallHandler,
    ) -> Any:
        """Intercept one asynchronous LangGraph ToolNode call."""
        tool_call = self._to_tool_call(request)
        self._check_step_limit(tool_call)
        started = self._record_tool_start(tool_call)
        self._apply_matching_perturbations(BeforeTool, tool_call)

        pending_failure = self._take_pending_failure(tool_call)
        if pending_failure is not None:
            response = self._tool_error(tool_call, RuntimeError(pending_failure.message))
            self._record_tool_end(tool_call, response, started)
            return response

        try:
            self._run_before_faults(tool_call)
            response = await handler(request)
        except Exception as error:
            response = self._tool_error(tool_call, error)
            self._record_tool_end(tool_call, response, started)
            return response

        response = self._finish_tool_call(tool_call, response)
        self._record_tool_end(tool_call, response, started)
        if getattr(response, "status", None) != "error":
            self._apply_matching_perturbations(AfterTool, tool_call)
        return response

    def _check_step_limit(self, tool_call: ToolCall) -> None:
        if len(self.trajectory) >= self.max_steps:
            self.step_limit_reached = True
            error = RuntimeError(
                f"LangGraph exceeded the limit of {self.max_steps} tool executions."
            )
            self.trace.record(
                kind="tool_call",
                phase="before_tool",
                name=tool_call.name,
                outcome="failed",
                call_id=tool_call.id,
                details={"error_type": type(error).__name__, "message": str(error)},
            )
            raise error

    def _record_tool_start(self, tool_call: ToolCall) -> float:
        started = self.trace.now()
        self.trace.record(
            kind="tool_call",
            phase="before_tool",
            name=tool_call.name,
            outcome="started",
            call_id=tool_call.id,
        )
        return started

    def _record_tool_end(
        self,
        tool_call: ToolCall,
        response: Any,
        started: float,
    ) -> None:
        failed = getattr(response, "status", None) == "error"
        self.trace.record(
            kind="tool_call",
            phase="after_tool",
            name=tool_call.name,
            outcome="failed" if failed else "succeeded",
            duration_ms=(self.trace.now() - started) * 1000.0,
            call_id=tool_call.id,
            details=(
                {"error": str(getattr(response, "content", ""))}
                if failed
                else {}
            ),
        )

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

            self.trace.record(
                kind="perturbation",
                phase=trigger.phase,
                name=type(perturbation).__name__,
                outcome=(
                    "queued"
                    if isinstance(perturbation, ToolFailurePerturbation)
                    else "applied"
                ),
                call_id=tool_call.id,
            )
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

    def _run_before_faults(self, tool_call: ToolCall) -> None:
        for trigger, fault in self.faults:
            if trigger.phase == "before_tool" and trigger.matches(tool_call):
                self.trace.record(
                    kind="fault",
                    phase="before_tool",
                    name=type(fault).__name__,
                    outcome="injected",
                    call_id=tool_call.id,
                )
                fault.before_execute(tool_call)

    def _finish_tool_call(self, tool_call: ToolCall, response: Any) -> Any:
        if getattr(response, "status", None) == "error":
            message = getattr(response, "content", "LangGraph tool returned an error.")
            self._record_failure(
                tool_call,
                RuntimeError(str(message) or "LangGraph tool returned an error."),
                observation=message,
            )
            return response

        matching_after_faults = [
            (trigger, fault)
            for trigger, fault in self.faults
            if trigger.phase == "after_tool" and trigger.matches(tool_call)
        ]
        if matching_after_faults:
            tool_message_type = import_module("langchain_core.messages").ToolMessage
            if not isinstance(response, tool_message_type):
                error = TypeError(
                    "Response-transform faults require a LangGraph ToolMessage; "
                    "Command responses cannot be rewritten by this interceptor."
                )
                return self._tool_error(tool_call, error)

            observed_response = response.content
            for trigger, fault in matching_after_faults:
                self.trace.record(
                    kind="fault",
                    phase=trigger.phase,
                    name=type(fault).__name__,
                    outcome="injected",
                    call_id=tool_call.id,
                )
                try:
                    observed_response = fault.after_execute(
                        tool_call,
                        observed_response,
                    )
                except Exception as error:
                    return self._tool_error(tool_call, error)

            response = tool_message_type(
                content=self._serialize_tool_content(observed_response),
                tool_call_id=tool_call.id or getattr(response, "tool_call_id", ""),
                name=getattr(response, "name", tool_call.name),
                status=getattr(response, "status", "success"),
            )

        self.trajectory.append(
            TrajectoryStep(
                tool_call=tool_call,
                observation=getattr(response, "content", response),
            )
        )
        return response

    def _tool_error(self, tool_call: ToolCall, error: Exception) -> Any:
        """Record a failure and return it as an observable LangGraph ToolMessage."""
        self._record_failure(tool_call, error)
        tool_message_type = import_module("langchain_core.messages").ToolMessage
        return tool_message_type(
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
        """Reject model responses whose batch was selected without state refresh."""
        candidate = getattr(response, "result", response)
        tool_calls = getattr(candidate, "tool_calls", None) or []
        if len(tool_calls) > 1:
            raise RuntimeError(
                "AgentFault's stateful LangGraph integration requires one tool call "
                "per model response. Split calls into separate graph/model turns."
            )


class LangGraphScenarioRunner:
    """Run a compiled LangGraph sync or async as an AgentFault scenario.

    Build ToolNode with both the interceptor's sync and async callbacks when
    supporting both execution modes. Model nodes that need model fault injection
    must route the underlying model call through interceptor.invoke_model or
    interceptor.ainvoke_model.
    """

    def __init__(
        self,
        scenario: Scenario,
        interceptor: LangGraphToolCallInterceptor,
    ) -> None:
        self.scenario = scenario
        self.interceptor = interceptor

    def _prepare(self) -> None:
        self.interceptor.environment = self.scenario.environment
        self.interceptor.perturbations = list(self.scenario.perturbations)
        self.interceptor.faults = list(self.scenario.faults)
        self.interceptor.trace.reset()
        self.interceptor.trace.record(
            kind="scenario",
            phase="run",
            name=self.scenario.name,
            outcome="started",
        )
        self.interceptor.model_call_executor.configure(
            self.scenario.model_faults,
            trace=self.interceptor.trace,
        )
        self.interceptor.reset()

    def run(self, inputs: Any, config: Any | None = None) -> ScenarioResult:
        """Invoke the graph synchronously and evaluate scenario assertions."""
        self._prepare()
        final_observation: Any = None
        terminal_error: Exception | None = None

        try:
            final_observation = self.scenario.agent.invoke(inputs, config=config)
        except Exception as error:
            terminal_error = error

        return self._evaluate(final_observation, terminal_error)

    async def arun(self, inputs: Any, config: Any | None = None) -> ScenarioResult:
        """Invoke the graph asynchronously and evaluate scenario assertions."""
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
                f"LangGraph reached the maximum of "
                f"{self.interceptor.max_steps} tool executions."
            )
        elif (
            terminal_error is None
            and self.scenario.model_faults
            and self.interceptor.model_call_executor.call_count == 0
        ):
            terminal_error = RuntimeError(
                "Scenario has model_faults, but this LangGraph did not route a model "
                "call through interceptor.invoke_model/ainvoke_model."
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
        outcome = (
            "passed" if passed else "error" if terminal_error is not None else "failed"
        )
        self.interceptor.trace.record(
            kind="scenario",
            phase="run",
            name=self.scenario.name,
            outcome=outcome,
            details={
                "assertions_passed": sum(result.passed for result in assertion_results),
                "assertions_total": len(assertion_results),
                "error_type": type(terminal_error).__name__ if terminal_error else None,
                "message": str(terminal_error) if terminal_error else None,
            },
        )

        return ScenarioResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=list(self.interceptor.trajectory),
            error=terminal_error,
            events=self.interceptor.trace.snapshot(),
        )
