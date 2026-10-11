from abc import ABC, abstractmethod

from agentfault.tools import ToolCall


class Trigger(ABC):
    """Select a tool event at which a perturbation or fault should run.

    Custom triggers may implement stateful matching and set phase to either
    "before_tool" or "after_tool". The default phase preserves historical
    behavior for custom triggers that only implement matches().
    """

    phase: str = "after_tool"

    @abstractmethod
    def matches(self, tool_call: ToolCall) -> bool:
        raise NotImplementedError
