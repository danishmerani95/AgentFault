from dataclasses import dataclass
from typing import Callable, Literal, TypeAlias

from agentfault.agent import Agent
from agentfault.testing import Scenario, ScenarioResult
from agentfault.tools import Tool, ToolRegistry

AgentFactory: TypeAlias = Callable[[str, list[Tool]], Agent]
CaseFactory: TypeAlias = Callable[[AgentFactory], tuple[Scenario, ToolRegistry]]
ScenarioExecutor: TypeAlias = Callable[[Scenario, ToolRegistry, int], ScenarioResult]
CaseStatus: TypeAlias = Literal["passed", "failed", "error"]


@dataclass(frozen=True)
class BenchmarkCase:
    """One reproducible behavioral test in a benchmark suite."""

    id: str
    title: str
    build: CaseFactory

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Benchmark case id must not be empty.")
        if not self.title.strip():
            raise ValueError("Benchmark case title must not be empty.")


@dataclass(frozen=True)
class BenchmarkSuite:
    """An immutable, versioned collection of benchmark cases."""

    id: str
    version: str
    category: str
    description: str
    cases: tuple[BenchmarkCase, ...]

    def __post_init__(self) -> None:
        for name in ("id", "version", "category", "description"):
            if not getattr(self, name).strip():
                raise ValueError(f"Benchmark suite {name} must not be empty.")
        if not self.cases:
            raise ValueError("Benchmark suite must contain at least one case.")
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Benchmark case ids must be unique within a suite.")


@dataclass(frozen=True)
class BenchmarkCaseResult:
    """Outcome and evidence for one benchmark case."""

    case_id: str
    title: str
    status: CaseStatus
    scenario_result: ScenarioResult | None = None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == "passed"


@dataclass(frozen=True)
class BenchmarkResult:
    """Aggregate results for one suite run."""

    suite_id: str
    suite_version: str
    category: str
    agent_name: str
    cases: tuple[BenchmarkCaseResult, ...]

    @property
    def complete(self) -> bool:
        return all(case.status in {"passed", "failed"} for case in self.cases)

    @property
    def score(self) -> float | None:
        """Return percentage passed, or None when any case was invalid."""
        if not self.complete or not self.cases:
            return None
        return round(100.0 * self.passed_count / len(self.cases), 2)

    @property
    def passed_count(self) -> int:
        return sum(case.status == "passed" for case in self.cases)

    @property
    def failed_count(self) -> int:
        return sum(case.status == "failed" for case in self.cases)

    @property
    def error_count(self) -> int:
        return sum(case.status == "error" for case in self.cases)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly summary without provider-specific object data."""
        return {
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "category": self.category,
            "agent_name": self.agent_name,
            "complete": self.complete,
            "score": self.score,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "errors": self.error_count,
            "cases": [
                {
                    "id": case.case_id,
                    "title": case.title,
                    "status": case.status,
                    "error": case.error,
                    "assertions": (
                        [
                            {
                                "passed": assertion.passed,
                                "message": assertion.message,
                            }
                            for assertion in case.scenario_result.assertions
                        ]
                        if case.scenario_result is not None
                        else []
                    ),
                    "tool_calls": (
                        [
                            {
                                "name": step.tool_call.name,
                                "succeeded": step.succeeded,
                                "error": step.error,
                            }
                            for step in case.scenario_result.trajectory
                        ]
                        if case.scenario_result is not None
                        else []
                    ),
                }
                for case in self.cases
            ],
        }
