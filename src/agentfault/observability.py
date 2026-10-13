"""Timestamped, ordered execution evidence for AgentFault scenarios."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    """One structured event in a scenario's execution timeline.

    Details should contain diagnostic metadata, not secrets, full prompts,
    tool arguments, or raw provider responses.
    """

    run_id: str
    sequence: int
    timestamp: str
    elapsed_ms: float
    kind: str
    phase: str
    name: str
    outcome: str
    duration_ms: float | None = None
    call_id: str | None = None
    details: dict[str, str | int | float | bool | None] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to JSON-friendly primitive values."""
        return asdict(self)


class TraceRecorder:
    """Build a monotonic timeline for one scenario run.

    Wall-clock ISO timestamps are useful when correlating with service logs;
    the elapsed and duration measurements use a monotonic clock so they remain
    meaningful if the system clock changes during a run.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Start a fresh trace with a new run identifier."""
        self.run_id = uuid4().hex
        self.started_at = perf_counter()
        self.started_timestamp = datetime.now(UTC)
        self.events: list[TraceEvent] = []

    def now(self) -> float:
        """Return the current monotonic timestamp for duration measurement."""
        return perf_counter()

    def record(
        self,
        *,
        kind: str,
        phase: str,
        name: str,
        outcome: str,
        duration_ms: float | None = None,
        call_id: str | None = None,
        details: dict[str, str | int | float | bool | None] | None = None,
    ) -> TraceEvent:
        """Append one event and return the recorded value."""
        event = TraceEvent(
            run_id=self.run_id,
            sequence=len(self.events) + 1,
            timestamp=datetime.now(UTC).isoformat(),
            elapsed_ms=round((perf_counter() - self.started_at) * 1000.0, 3),
            kind=kind,
            phase=phase,
            name=name,
            outcome=outcome,
            duration_ms=(
                round(duration_ms, 3) if duration_ms is not None else None
            ),
            call_id=call_id,
            details=dict(details or {}),
        )
        self.events.append(event)
        return event

    def snapshot(self) -> list[TraceEvent]:
        """Return a defensive copy of the recorded events."""
        return list(self.events)
