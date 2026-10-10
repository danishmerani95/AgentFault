from abc import ABC, abstractmethod
from typing import Any

from agentfault.tools.registry import ToolRegistry
from agentfault.tools.tool import ToolCall


class ToolExecutor(ABC):
    @abstractmethod
    def execute(self, tool_call: ToolCall) -> Any:
        raise NotImplementedError


class RegistryToolExecutor(ToolExecutor):
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def execute(self, tool_call: ToolCall) -> Any:
        return self.tool_registry.execute(tool_call)
