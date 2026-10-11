from abc import ABC
from typing import Any

from agentfault.tools import ToolCall


class ToolFault(ABC):
    """A fault injected at a tool boundary.

    Pair a fault with a Trigger in Scenario.faults. BeforeTool triggers call
    before_execute before the real tool; AfterTool triggers call after_execute
    with the real tool's response. Subclasses may override either hook.
    """

    def before_execute(self, tool_call: ToolCall) -> None:
        """Inject a pre-execution fault. The default leaves execution unchanged."""

    def after_execute(self, tool_call: ToolCall, response: Any) -> Any:
        """Transform a successful tool response. The default returns it unchanged."""
        return response
