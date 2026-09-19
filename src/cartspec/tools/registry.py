from typing import Any

from cartspec.tools import Tool, ToolCall


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = {tool.name: tool for tool in tools}

    def execute(self, tool_call: ToolCall) -> Any:
        tool = self.tools.get(tool_call.name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_call.name}")
        return tool.execute(**tool_call.arguments)
