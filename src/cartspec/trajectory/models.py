from dataclasses import dataclass
from typing import Any

from cartspec.tools.tool import ToolCall


@dataclass
class TrajectoryStep:
    tool_call: ToolCall
    observation: Any
    error: dict[str, str] | None = None

    @property
    def succeeded(self) -> bool:
        """Whether the tool call completed successfully."""
        return self.error is None
