from abc import ABC, abstractmethod

from agentfault.tools import ToolCall


class Trigger(ABC):
    @abstractmethod
    def matches(self, tool_call: ToolCall) -> bool:
        raise NotImplementedError
