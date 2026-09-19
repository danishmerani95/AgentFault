from dataclasses import dataclass

from cartspec.testing.assertion import AssertionResult
from cartspec.trajectory import TrajectoryStep


@dataclass
class TestResult:
    __test__ = False

    passed: bool
    assertions: list[AssertionResult]
    trajectory: list[TrajectoryStep]
