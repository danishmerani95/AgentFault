from dataclasses import dataclass, field
from typing import Any

from agentfault.testing.assertion import Assertion
from agentfault.testing.faults import ToolFault
from agentfault.testing.perturbations import Perturbation
from agentfault.testing.triggers import Trigger

PerturbationSchedule = tuple[Trigger, Perturbation]
FaultSchedule = tuple[Trigger, ToolFault]


@dataclass
class Scenario:
    __test__ = False

    name: str
    agent: Any
    environment: Any
    perturbations: list[PerturbationSchedule] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    faults: list[FaultSchedule] = field(default_factory=list)
