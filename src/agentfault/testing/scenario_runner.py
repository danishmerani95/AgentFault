from typing import Any

from agentfault.observability import TraceRecorder
from agentfault.testing.assertion import AssertionResult, EvaluationContext
from agentfault.testing.faults import ModelCallExecutor
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.runner import AgentRunner
from agentfault.testing.scenario import FaultSchedule, Scenario
from agentfault.testing.scenario_result import ScenarioResult
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
        trace: TraceRecorder | None = None,
    ) -> None:
        self.tool_executor = tool_executor
        self.faults = list(faults or [])
        self.trace = trace
        self.pending_failures: list[ToolFailurePerturbation] = []

    def queue_failure(self, perturbation: ToolFailurePerturbation) -> None:
        self.pending_failures.append(perturbation)

    def execute(self, tool_call: ToolCall) -> Any:
        started = self.trace.now() if self.trace is not None else 0.0
        if self.trace is not None:
            self.trace.record(
                kind="tool_call",
                phase="before_tool",
                name=tool_call.name,
                outcome="started",
                call_id=tool_call.id,
            )

        try:
            for trigger, fault in self.faults:
                if trigger.phase == "before_tool" and trigger.matches(tool_call):
                    self._record_fault(tool_call, trigger.phase, fault)
                    fault.before_execute(tool_call)

            for index, perturbation in enumerate(self.pending_failures):
                if perturbation.matches(tool_call):
                    del self.pending_failures[index]
                    self._record_perturbation(tool_call, perturbation)
                    perturbation.apply(None)
                    break

            response = self.tool_executor.execute(tool_call)

            for trigger, fault in self.faults:
                if trigger.phase == "after_tool" and trigger.matches(tool_call):
                    self._record_fault(tool_call, trigger.phase, fault)
                    response = fault.after_execute(tool_call, response)
        except ToolExecutionFailure as failure:
            self._record_tool_failure(tool_call, failure.original_error, started)
            raise
        except Exception as error:
            self._record_tool_failure(tool_call, error, started)
            raise ToolExecutionFailure(tool_call.name, error) from error

        if self.trace is not None:
            self.trace.record(
                kind="tool_call",
                phase="after_tool",
                name=tool_call.name,
                outcome="succeeded",
                duration_ms=(self.trace.now() - started) * 1000.0,
                call_id=tool_call.id,
            )
        return response

    def _record_tool_failure(
        self,
        tool_call: ToolCall,
        error: Exception,
        started: float,
    ) -> None:
        if self.trace is not None:
            self.trace.record(
                kind="tool_call",
                phase="after_tool",
                name=tool_call.name,
                outcome="failed",
                duration_ms=(self.trace.now() - started) * 1000.0,
                call_id=tool_call.id,
                details={
                    "error_type": type(error).__name__,
                    "message": str(error) or type(error).__name__,
                },
            )

    def _record_fault(self, tool_call: ToolCall, phase: str, fault: Any) -> None:
        if self.trace is not None:
            self.trace.record(
                kind="fault",
                phase=phase,
                name=type(fault).__name__,
                outcome="injected",
                call_id=tool_call.id,
            )

    def _record_perturbation(
        self,
        tool_call: ToolCall,
        perturbation: Any,
    ) -> None:
        if self.trace is not None:
            self.trace.record(
                kind="perturbation",
                phase="before_tool",
                name=type(perturbation).__name__,
                outcome="applied",
                call_id=tool_call.id,
            )


class ScenarioRunner:
    __test__ = False

    def __init__(self, tool_registry: ToolRegistry, max_steps: int = 100) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def run(self, scenario: Scenario) -> ScenarioResult:
        trace = TraceRecorder()
        trace.record(
            kind="scenario",
            phase="run",
            name=scenario.name,
            outcome="started",
        )
        tool_executor = _PerturbableToolExecutor(
            RegistryToolExecutor(self.tool_registry),
            faults=scenario.faults,
            trace=trace,
        )

        def apply_matching_perturbations(
            phase: str, tool_call: ToolCall
        ) -> None:
            for trigger, perturbation in scenario.perturbations:
                if trigger.phase == phase and trigger.matches(tool_call):
                    if isinstance(perturbation, ToolFailurePerturbation):
                        tool_executor.queue_failure(perturbation)
                    else:
                        if trace is not None:
                            trace.record(
                                kind="perturbation",
                                phase=phase,
                                name=type(perturbation).__name__,
                                outcome="applied",
                                call_id=tool_call.id,
                            )
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
        final_observation: Any = None
        terminal_error: Exception | None = None
        model_call_executor = getattr(scenario.agent, "model_call_executor", None)
        if isinstance(model_call_executor, ModelCallExecutor):
            # Reset schedules for every scenario, including an empty list, so
            # faults cannot leak between runs if an adapter instance is reused.
            model_call_executor.configure(scenario.model_faults, trace=trace)
        elif scenario.model_faults:
            terminal_error = RuntimeError(
                "Scenario has model_faults, but the agent must expose a "
                "ModelCallExecutor and route model-client calls through it."
            )

        if terminal_error is None:
            try:
                final_observation = agent_runner.run()
            except Exception as error:
                # Model/provider or agent failures are scenario execution errors,
                # not tool failures. Preserve earlier tool trajectory as evidence.
                terminal_error = error

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
        outcome = (
            "passed" if passed else "error" if terminal_error is not None else "failed"
        )
        trace.record(
            kind="scenario",
            phase="run",
            name=scenario.name,
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
            trajectory=agent_runner.trajectory,
            error=terminal_error,
            events=trace.snapshot(),
        )
