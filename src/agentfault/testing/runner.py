from copy import deepcopy
from typing import Any, Callable

from agentfault.agent import Agent
from agentfault.tools import (
    RegistryToolExecutor,
    ToolCall,
    ToolExecutionFailure,
    ToolExecutor,
    ToolRegistry,
)
from agentfault.trajectory import TrajectoryStep


class ToolExecutionErrorObservation(dict[str, str]):
    """Serializable feedback describing a failed tool execution."""

    def __init__(self, tool_call: ToolCall, error: Exception) -> None:
        super().__init__(
            type="tool_error",
            tool_name=tool_call.name,
            error_type=type(error).__name__,
            message=str(error) or type(error).__name__,
        )


ToolExecutionHook = Callable[[ToolCall, Any], None]
BeforeToolCallExecutionHook = Callable[[ToolCall], None]
ToolErrorHook = Callable[[ToolCall, Exception], None]


class AgentRunner:
    def __init__(
        self,
        agent: Agent,
        tool_executor: ToolExecutor | None = None,
        tool_registry: ToolRegistry | None = None,
        before_tool_execution: BeforeToolCallExecutionHook | None = None,
        on_tool_executed: ToolExecutionHook | None = None,
        on_tool_error: ToolErrorHook | None = None,
        max_steps: int = 100,
    ) -> None:
        if tool_executor is None:
            if tool_registry is None:
                raise ValueError("AgentRunner requires a tool executor or registry.")
            tool_executor = RegistryToolExecutor(tool_registry)
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self.agent = agent
        self.tool_executor = tool_executor
        self.trajectory: list[TrajectoryStep] = []
        self.before_tool_execution = before_tool_execution
        self.on_tool_executed = on_tool_executed
        self.on_tool_error = on_tool_error
        self.max_steps = max_steps
        self.step_limit_reached = False

    def run(self) -> Any:
        observation: Any = None

        while len(self.trajectory) < self.max_steps:
            # Keep agent decisions and pre-execution hooks outside the executor
            # exception handler. Their failures must not look like tool errors.
            tool_call = self.agent.next_action(observation)

            if tool_call is None:
                return observation

            if self.before_tool_execution is not None:
                self.before_tool_execution(tool_call)

            try:
                observation = self.tool_executor.execute(tool_call)
            except ToolExecutionFailure as failure:
                error = failure.original_error
                failure_observation = ToolExecutionErrorObservation(tool_call, error)
                self.trajectory.append(
                    TrajectoryStep(
                        tool_call=tool_call,
                        observation=dict(failure_observation),
                        error={
                            "type": failure_observation["error_type"],
                            "message": failure_observation["message"],
                        },
                    )
                )
                if self.on_tool_error is not None:
                    self.on_tool_error(tool_call, error)
                observation = dict(failure_observation)
                continue

            snapshot = deepcopy(observation)
            self.trajectory.append(
                TrajectoryStep(
                    tool_call=tool_call,
                    observation=snapshot,
                )
            )

            if self.on_tool_executed is not None:
                self.on_tool_executed(tool_call, snapshot)

            observation = snapshot

        self.step_limit_reached = True
        return observation
