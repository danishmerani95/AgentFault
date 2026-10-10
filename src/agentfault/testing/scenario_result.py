from dataclasses import dataclass

from agentfault.testing.assertion import AssertionResult
from agentfault.trajectory import TrajectoryStep


@dataclass
class ScenarioResult:
    __test__ = False

    passed: bool
    assertions: list[AssertionResult]
    trajectory: list[TrajectoryStep]
    error: Exception | None = None
