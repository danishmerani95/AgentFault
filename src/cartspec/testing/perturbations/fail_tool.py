from dataclasses import dataclass
from typing import Any

from cartspec.testing.perturbations.base import Perturbation
from cartspec.tools import ToolCall


@dataclass
class ToolFailurePerturbation(Perturbation):
    tool_name: str | None = None
    message: str = "Tool execution failed."

    def apply(self, environment: Any) -> None:
        raise RuntimeError(self.message)

    def matches(self, tool_call: ToolCall) -> bool:
        return self.tool_name is None or tool_call.name == self.tool_name


class FailTool(ToolFailurePerturbation):
    def __init__(self, message: str = "Tool execution failed.") -> None:
        super().__init__(tool_name=None, message=message)
