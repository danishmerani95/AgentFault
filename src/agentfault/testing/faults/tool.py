import json
import time
from collections.abc import Callable
from typing import Any

from agentfault.testing.faults.base import ToolFault
from agentfault.tools import ToolCall


class ToolTimeoutFault(ToolFault):
    """Raise a deterministic timeout before the matched tool is executed."""

    def __init__(self, message: str = "Injected tool timeout.") -> None:
        self.message = message

    def before_execute(self, tool_call: ToolCall) -> None:
        raise TimeoutError(self.message)


class TransientToolFailureFault(ToolFault):
    """Fail the next matching executions, then allow execution."""

    def __init__(
        self,
        failures: int = 1,
        message: str = "Injected transient tool failure.",
    ) -> None:
        if failures < 1:
            raise ValueError("failures must be at least 1.")
        self.remaining = failures
        self.message = message

    def before_execute(self, tool_call: ToolCall) -> None:
        if self.remaining:
            self.remaining -= 1
            raise RuntimeError(self.message)


class LatencyFault(ToolFault):
    """Delay the selected tool boundary.

    The trigger decides the boundary: BeforeTool sleeps before the real tool,
    while AfterTool sleeps after the tool returns but before the agent sees
    the result. Inject sleeper in tests to avoid wall-clock delays.
    """

    def __init__(
        self,
        delay_seconds: float,
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative.")
        self.delay_seconds = delay_seconds
        self.sleeper = sleeper

    def before_execute(self, tool_call: ToolCall) -> None:
        self.sleeper(self.delay_seconds)

    def after_execute(self, tool_call: ToolCall, response: Any) -> Any:
        self.sleeper(self.delay_seconds)
        return response


class MalformedResponseFault(ToolFault):
    """Replace a tool response with a malformed value for parser/recovery tests."""

    def __init__(self, response: Any = "{malformed-json") -> None:
        self.response = response

    def after_execute(self, tool_call: ToolCall, response: Any) -> Any:
        return self.response


class TruncatedResponseFault(ToolFault):
    """Truncate a string, byte string, list, tuple, or JSON-serializable value."""

    def __init__(self, max_length: int) -> None:
        if max_length < 0:
            raise ValueError("max_length must not be negative.")
        self.max_length = max_length

    def after_execute(self, tool_call: ToolCall, response: Any) -> Any:
        if isinstance(response, str):
            return response[: self.max_length]
        if isinstance(response, bytes):
            return response[: self.max_length]
        if isinstance(response, list):
            return response[: self.max_length]
        if isinstance(response, tuple):
            return response[: self.max_length]
        return json.dumps(response, default=str)[: self.max_length]


class EmptyResponseFault(ToolFault):
    """Replace a successful tool response with None."""

    def after_execute(self, tool_call: ToolCall, response: Any) -> None:
        return None
