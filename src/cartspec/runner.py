from typing import Any

from cartspec.agent import Agent
from cartspec.tool import ToolRegistry


class AgentRunner:
    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
    ) -> None:
        self.agent = agent
        self.tool_registry = tool_registry

    def run(self) -> Any:
        observation: Any = None

        while True:
            tool_call = self.agent.next_action(observation)

            if tool_call is None:
                return observation

            observation = self.tool_registry.execute(tool_call)
