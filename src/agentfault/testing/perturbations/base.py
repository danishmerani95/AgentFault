from abc import ABC, abstractmethod
from typing import Any


class Perturbation(ABC):
    @abstractmethod
    def apply(self, environment: Any) -> None:
        raise NotImplementedError
