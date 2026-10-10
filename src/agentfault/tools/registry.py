from typing import Any

from agentfault.tools.errors import ToolExecutionFailure
from agentfault.tools.tool import Tool, ToolCall


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = {tool.name: tool for tool in tools}

    def execute(self, tool_call: ToolCall) -> Any:
        tool = self.tools.get(tool_call.name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_call.name}")

        try:
            return tool.execute(**tool_call.arguments)
        except ToolExecutionFailure:
            raise
        except Exception as error:
            # Only exceptions from an actual registered tool invocation are
            # classified as recoverable tool failures. Registry/configuration
            # errors and agent/provider/hook errors are not caught here.
            raise ToolExecutionFailure(tool_call.name, error) from error
