from dataclasses import dataclass, field

from agentfault.testing.assertion import AssertionResult
from agentfault.trajectory import TrajectoryStep
from agentfault.observability import TraceEvent


@dataclass
class ScenarioResult:
    __test__ = False

    passed: bool
    assertions: list[AssertionResult]
    trajectory: list[TrajectoryStep]
    error: Exception | None = None
    events: list[TraceEvent] = field(default_factory=list)
