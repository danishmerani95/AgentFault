from typing import Any

from agentfault.agent.base import Agent
from agentfault.tools.tool import ToolCall


class FailingAgent(Agent):
    def __init__(self) -> None:
        self.call_count = 0

    def next_action(self, observation: Any) -> ToolCall | None:
        self.call_count += 1

        if self.call_count == 1:
            return ToolCall(
                name="failing_tool",
                arguments={},
            )

        return None
