from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Tool:
    name: str
    description: str
    function: Callable[..., Any]

    def execute(self, **arguments: Any) -> Any:
        return self.function(**arguments)
    
@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    
class ToolRegistry: 
    def __init__(self, tools: list[Tool]) -> None: 
        self.tools = {tool.name: tool for tool in tools} 
        
    def execute(self, tool_call: ToolCall) -> Any: 
        tool = self.tools.get(tool_call.name) 
        if tool is None: 
            raise ValueError(f"Unknown tool: {tool_call.name}") 
        return tool.execute(**tool_call.arguments)