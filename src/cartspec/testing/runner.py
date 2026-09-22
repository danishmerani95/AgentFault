from copy import deepcopy
from typing import Any, Callable

from cartspec.agent import Agent
from cartspec.tools import ToolCall, ToolRegistry
from cartspec.trajectory import TrajectoryStep

ToolExecutionHook = Callable[[ToolCall, Any], None]
BeforeToolCallExecutionHook = Callable[[ToolCall], None]


class AgentRunner:
    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
        before_tool_execution: BeforeToolCallExecutionHook | None = None,
        on_tool_executed: ToolExecutionHook | None = None,
    ) -> None:
        self.agent = agent
        self.tool_registry = tool_registry
        self.trajectory: list[TrajectoryStep] = []
        self.before_tool_execution = before_tool_execution
        self.on_tool_executed = on_tool_executed

    def run(self) -> Any:
        observation: Any = None

        while True:
            tool_call = self.agent.next_action(observation)

            if tool_call is None:
                return observation

            if self.before_tool_execution is not None:
                self.before_tool_execution(tool_call)

            observation = self.tool_registry.execute(tool_call)

            snapshot = deepcopy(observation)

            self.trajectory.append(
                TrajectoryStep(
                    tool_call=tool_call,
                    observation=snapshot,
                )
            )

            if self.on_tool_executed is not None:
                self.on_tool_executed(tool_call, snapshot)
