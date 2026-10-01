from dataclasses import dataclass, field
from typing import Any

from cartspec.testing.assertion import Assertion
from cartspec.testing.triggers.tool import ToolTrigger


@dataclass
class Scenario:
    __test__ = False

    name: str
    agent: Any
    environment: Any
    perturbations: list[ToolTrigger] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
