from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias, TypeVar

from agentfault.observability import TraceRecorder
from agentfault.testing.triggers.model import ModelCallTrigger

T = TypeVar("T")
ModelCallSchedule: TypeAlias = tuple[ModelCallTrigger, "ModelCallFault"]


class ModelCallFault:
    """Inject a fault before or after an actual model-client invocation.

    Fault objects are stateful; by default the built-in faults affect one matched
    call. A schedule determines which call number and phase invokes each hook.
    """

    def before_call(self, call_number: int) -> None:
        """Inject a model API fault before the underlying client is called."""

    def after_call(self, call_number: int, response: Any) -> Any:
        """Transform a model response. The default preserves it."""
        return response


class InjectedModelAPIError(RuntimeError):
    """Provider-neutral simulated model API error with HTTP-like metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_type: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.retryable = retryable


class _OneShotModelFault(ModelCallFault):
    def __init__(self, times: int = 1) -> None:
        if times < 1:
            raise ValueError("times must be at least 1.")
        self.remaining = times

    def _consume(self) -> bool:
        if self.remaining < 1:
            return False
        self.remaining -= 1
        return True


class ModelTimeoutFault(_OneShotModelFault):
    """Raise a simulated timeout before the configured model API call."""

    def __init__(self, message: str = "Injected model API timeout.", times: int = 1) -> None:
        super().__init__(times)
        self.message = message

    def before_call(self, call_number: int) -> None:
        if self._consume():
            raise TimeoutError(self.message)


class ModelRateLimitFault(_OneShotModelFault):
    """Simulate a retryable HTTP 429 rate-limit response."""

    def __init__(
        self,
        message: str = "Injected model API rate limit.",
        times: int = 1,
    ) -> None:
        super().__init__(times)
        self.message = message

    def before_call(self, call_number: int) -> None:
        if self._consume():
            raise InjectedModelAPIError(
                self.message,
                status_code=429,
                error_type="rate_limit",
                retryable=True,
            )


class ModelServerErrorFault(_OneShotModelFault):
    """Simulate a retryable provider HTTP 5xx failure."""

    def __init__(
        self,
        status_code: int = 503,
        message: str = "Injected model API server error.",
        times: int = 1,
    ) -> None:
        if status_code < 500 or status_code > 599:
            raise ValueError("status_code must be in the 500–599 range.")
        super().__init__(times)
        self.status_code = status_code
        self.message = message

    def before_call(self, call_number: int) -> None:
        if self._consume():
            raise InjectedModelAPIError(
                self.message,
                status_code=self.status_code,
                error_type="server_error",
                retryable=True,
            )


class ModelConnectionFault(_OneShotModelFault):
    """Simulate a network/connection error before a model request."""

    def __init__(self, message: str = "Injected model connection failure.", times: int = 1) -> None:
        super().__init__(times)
        self.message = message

    def before_call(self, call_number: int) -> None:
        if self._consume():
            raise ConnectionError(self.message)


class MalformedModelResponseFault(_OneShotModelFault):
    """Return a configured malformed SDK response instead of the true response."""

    def __init__(self, response: Any = None, times: int = 1) -> None:
        super().__init__(times)
        self.response = response

    def after_call(self, call_number: int, response: Any) -> Any:
        if self._consume():
            return self.response
        return response


class EmptyModelResponseFault(_OneShotModelFault):
    """Replace a successful SDK response with None."""

    def __init__(self, times: int = 1) -> None:
        super().__init__(times)

    def after_call(self, call_number: int, response: Any) -> Any:
        if self._consume():
            return None
        return response


class ModelLatencyFault(_OneShotModelFault):
    """Delay a model call boundary; use an injected sleeper in tests."""

    def __init__(
        self,
        delay_seconds: float,
        *,
        sleeper: Callable[[float], None] = time.sleep,
        times: int = 1,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative.")
        super().__init__(times)
        self.delay_seconds = delay_seconds
        self.sleeper = sleeper

    def before_call(self, call_number: int) -> None:
        if self._consume():
            self.sleeper(self.delay_seconds)

    def after_call(self, call_number: int, response: Any) -> Any:
        if self._consume():
            self.sleeper(self.delay_seconds)
        return response


class ModelCallExecutor:
    """Apply scheduled model-call faults around a real SDK/framework call."""

    def __init__(
        self,
        schedules: list[ModelCallSchedule] | None = None,
        trace: TraceRecorder | None = None,
    ) -> None:
        self.schedules = list(schedules or [])
        self.call_count = 0
        self.trace = trace

    def configure(
        self,
        schedules: list[ModelCallSchedule],
        *,
        trace: TraceRecorder | None = None,
    ) -> None:
        """Set this scenario's schedules and reset the model-call counter."""
        self.schedules = list(schedules)
        self.call_count = 0
        self.trace = trace

    def execute(self, call: Callable[[], T]) -> T:
        self.call_count += 1
        call_number = self.call_count
        call_id = f"model-{call_number}"
        started = self.trace.now() if self.trace is not None else 0.0
        if self.trace is not None:
            self.trace.record(
                kind="model_call",
                phase="before_model",
                name="model",
                outcome="started",
                call_id=call_id,
                details={"call_number": call_number},
            )

        try:
            self._inject_before_faults(call_number, call_id)
            response = call()
            for trigger, fault in self.schedules:
                if trigger.phase == "after_model" and trigger.matches(call_number):
                    self._record_injected_fault(call_id, trigger.phase, fault)
                    response = fault.after_call(call_number, response)
            if self.trace is not None:
                self.trace.record(
                    kind="model_call",
                    phase="after_model",
                    name="model",
                    outcome="succeeded",
                    duration_ms=(
                        (self.trace.now() - started) * 1000.0
                        if self.trace is not None else None
                    ),
                    call_id=call_id,
                    details={"call_number": call_number},
                )
            return response
        except Exception as error:
            if self.trace is not None:
                self.trace.record(
                    kind="model_call",
                    phase="after_model",
                    name="model",
                    outcome="failed",
                    duration_ms=(self.trace.now() - started) * 1000.0,
                    call_id=call_id,
                    details={
                        "call_number": call_number,
                        "error_type": type(error).__name__,
                        "message": str(error) or type(error).__name__,
                    },
                )
            raise

    async def execute_async(self, call: Callable[[], Awaitable[T]]) -> T:
        """Apply the same scenario schedule around an asynchronous model call."""
        self.call_count += 1
        call_number = self.call_count
        call_id = f"model-{call_number}"
        started = self.trace.now() if self.trace is not None else 0.0
        if self.trace is not None:
            self.trace.record(
                kind="model_call",
                phase="before_model",
                name="model",
                outcome="started",
                call_id=call_id,
                details={"call_number": call_number},
            )

        try:
            self._inject_before_faults(call_number, call_id)
            response = await call()
            for trigger, fault in self.schedules:
                if trigger.phase == "after_model" and trigger.matches(call_number):
                    self._record_injected_fault(call_id, trigger.phase, fault)
                    response = fault.after_call(call_number, response)
            if self.trace is not None:
                self.trace.record(
                    kind="model_call",
                    phase="after_model",
                    name="model",
                    outcome="succeeded",
                    duration_ms=(self.trace.now() - started) * 1000.0,
                    call_id=call_id,
                    details={"call_number": call_number},
                )
            return response
        except Exception as error:
            if self.trace is not None:
                self.trace.record(
                    kind="model_call",
                    phase="after_model",
                    name="model",
                    outcome="failed",
                    duration_ms=(self.trace.now() - started) * 1000.0,
                    call_id=call_id,
                    details={
                        "call_number": call_number,
                        "error_type": type(error).__name__,
                        "message": str(error) or type(error).__name__,
                    },
                )
            raise

    def _inject_before_faults(self, call_number: int, call_id: str) -> None:
        for trigger, fault in self.schedules:
            if trigger.phase == "before_model" and trigger.matches(call_number):
                self._record_injected_fault(call_id, trigger.phase, fault)
                fault.before_call(call_number)

    def _record_injected_fault(
        self,
        call_id: str,
        phase: str,
        fault: ModelCallFault,
    ) -> None:
        if self.trace is not None:
            self.trace.record(
                kind="fault",
                phase=phase,
                name=type(fault).__name__,
                outcome="injected",
                call_id=call_id,
            )
