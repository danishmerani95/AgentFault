from dataclasses import dataclass
from abc import ABC, abstractmethod


class ModelCallTrigger(ABC):
    """Select a model-call boundary, independent from named tool calls."""

    phase: str

    @abstractmethod
    def matches(self, call_number: int) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class BeforeModelCall(ModelCallTrigger):
    """Match before a model invocation. Omit call_number to match every call."""

    call_number: int | None = None
    phase = "before_model"

    def __post_init__(self) -> None:
        if self.call_number is not None and self.call_number < 1:
            raise ValueError("call_number must be at least 1.")

    def matches(self, call_number: int) -> bool:
        return self.call_number is None or self.call_number == call_number


@dataclass(frozen=True)
class AfterModelCall(ModelCallTrigger):
    """Match after a model invocation. Omit call_number to match every call."""

    call_number: int | None = None
    phase = "after_model"

    def __post_init__(self) -> None:
        if self.call_number is not None and self.call_number < 1:
            raise ValueError("call_number must be at least 1.")

    def matches(self, call_number: int) -> bool:
        return self.call_number is None or self.call_number == call_number
