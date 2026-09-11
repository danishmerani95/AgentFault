from abc import ABC, abstractmethod

from cartspec.tool import ToolCall


class Agent(ABC):
    @abstractmethod
    def next_action(self, observation: object) -> ToolCall | None:
        """Return the next tool call based on the current observation."""
        raise NotImplementedError
