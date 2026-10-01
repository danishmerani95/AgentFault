from dataclasses import dataclass

from cartspec.testing.perturbations import Perturbation


@dataclass
class ToolTrigger:
    tool_name: str
    perturbation: Perturbation
