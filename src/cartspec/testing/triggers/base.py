from abc import ABC, abstractmethod

from cartspec.tools import ToolCall


class Trigger(ABC):
    @abstractmethod
    def matches(self, tool_call: ToolCall) -> bool:
        raise NotImplementedError
