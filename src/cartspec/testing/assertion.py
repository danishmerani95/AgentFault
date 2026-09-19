from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AssertionResult:
    passed: bool
    message: str


class Assertion(ABC):
    @abstractmethod
    def check(
        self,
        result: Any,
        trajectory: Any,
    ) -> AssertionResult:
        raise NotImplementedError
