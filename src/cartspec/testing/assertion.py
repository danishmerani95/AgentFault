from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from cartspec.trajectory import TrajectoryStep


@dataclass
class EvaluationContext:
    """Evidence available to assertions after a scenario has executed."""

    final_observation: Any
    trajectory: list[TrajectoryStep]
    error: Exception | None
    environment: Any


@dataclass
class AssertionResult:
    passed: bool
    message: str


class Assertion(ABC):
    @abstractmethod
    def check(self, context: EvaluationContext) -> AssertionResult:
        raise NotImplementedError
