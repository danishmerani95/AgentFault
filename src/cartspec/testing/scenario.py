from dataclasses import dataclass, field
from typing import Any

from cartspec.testing.assertion import Assertion
from cartspec.testing.perturbations import Perturbation
from cartspec.testing.triggers import Trigger

PerturbationSchedule = tuple[Trigger, Perturbation]


@dataclass
class Scenario:
    __test__ = False

    name: str
    agent: Any
    environment: Any
    perturbations: list[PerturbationSchedule] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
