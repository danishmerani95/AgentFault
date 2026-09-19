from dataclasses import dataclass
from typing import Any

from cartspec.tools.tool import ToolCall


@dataclass
class TrajectoryStep:
    tool_call: ToolCall
    observation: Any
