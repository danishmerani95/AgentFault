from dataclasses import dataclass

from agentfault.testing.triggers.base import Trigger
from agentfault.tools import ToolCall


@dataclass
class BeforeTool(Trigger):
    tool_name: str

    def matches(self, tool_call: ToolCall) -> bool:
        return tool_call.name == self.tool_name


@dataclass(frozen=True)
class AfterTool(Trigger):
    tool_name: str

    def matches(self, tool_call: ToolCall) -> bool:
        return tool_call.name == self.tool_name
