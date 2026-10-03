from typing import Any

from cartspec.testing.perturbations.base import Perturbation


class FailTool(Perturbation):
    def __init__(self, message: str = "Tool execution failed.") -> None:
        self.message = message

    def apply(self, environment: Any) -> None:
        raise RuntimeError(self.message)
