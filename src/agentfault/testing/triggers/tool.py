from dataclasses import dataclass

from agentfault.testing.triggers.base import Trigger
from agentfault.tools import ToolCall


@dataclass
class BeforeTool(Trigger):
    phase = "before_tool"
    tool_name: str

    def matches(self, tool_call: ToolCall) -> bool:
        return tool_call.name == self.tool_name


@dataclass(frozen=True)
class AfterTool(Trigger):
    phase = "after_tool"
    tool_name: str

    def matches(self, tool_call: ToolCall) -> bool:
        return tool_call.name == self.tool_name
