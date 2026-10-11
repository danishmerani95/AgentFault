from dataclasses import dataclass
from statistics import fmean, pstdev
from typing import Any

from agentfault.benchmarks.models import (
    AgentFactory,
    BenchmarkResult,
    BenchmarkSuite,
)
from agentfault.benchmarks.runner import BenchmarkRunner


@dataclass(frozen=True)
class RepeatedBenchmarkResult:
    """Results and reliability statistics across independent suite repetitions.

    Pass rates are fractions from 0.0 to 1.0. The score mean and standard
    deviation are reported only when every repetition produced a valid,
    complete benchmark result; errored repetitions must not be silently dropped.
    """

    suite_id: str
    suite_version: str
    agent_name: str
    runs: tuple[BenchmarkResult, ...]

    @property
    def repetitions(self) -> int:
        return len(self.runs)

    @property
    def complete(self) -> bool:
        return bool(self.runs) and all(run.complete for run in self.runs)

    @property
    def score_mean(self) -> float | None:
        if not self.complete:
            return None
        scores = [run.score for run in self.runs]
        if not scores or any(score is None for score in scores):
            return None
        return round(fmean(score for score in scores if score is not None), 2)

    @property
    def score_stddev(self) -> float | None:
        if not self.complete:
            return None
        scores = [run.score for run in self.runs]
        if not scores or any(score is None for score in scores):
            return None
        return round(pstdev(score for score in scores if score is not None), 2)

    @property
    def pass_k(self) -> float:
        """Fraction of benchmark tasks passed in every repetition (tau-bench style)."""
        if not self.runs:
            return 0.0
        case_ids = [case.case_id for case in self.runs[0].cases]
        if not case_ids:
            return 0.0
        passed_every_time = 0
        for case_id in case_ids:
            if all(
                any(case.case_id == case_id and case.status == "passed" for case in run.cases)
                for run in self.runs
            ):
                passed_every_time += 1
        return round(passed_every_time / len(case_ids), 4)

    @property
    def per_case_pass_rate(self) -> dict[str, float]:
        if not self.runs:
            return {}
        case_ids = [case.case_id for case in self.runs[0].cases]
        rates: dict[str, float] = {}
        for case_id in case_ids:
            passed = sum(
                any(case.case_id == case_id and case.status == "passed" for case in run.cases)
                for run in self.runs
            )
            rates[case_id] = round(passed / len(self.runs), 4)
        return rates

    @property
    def error_count(self) -> int:
        return sum(run.error_count for run in self.runs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "agent_name": self.agent_name,
            "repetitions": self.repetitions,
            "complete": self.complete,
            "score_mean": self.score_mean,
            "score_stddev": self.score_stddev,
            "pass_k": self.pass_k,
            "per_case_pass_rate": self.per_case_pass_rate,
            "error_count": self.error_count,
            "runs": [
                {
                    "complete": run.complete,
                    "score": run.score,
                    "passed": run.passed_count,
                    "failed": run.failed_count,
                    "errors": run.error_count,
                }
                for run in self.runs
            ],
        }


class RepeatedBenchmarkRunner:
    """Run a suite repeatedly to measure stochastic agent reliability."""

    def __init__(self, max_steps: int = 100) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.max_steps = max_steps

    def run(
        self,
        suite: BenchmarkSuite,
        agent_factory: AgentFactory,
        *,
        repetitions: int = 5,
        agent_name: str = "custom-agent",
    ) -> RepeatedBenchmarkResult:
        if repetitions < 1:
            raise ValueError("repetitions must be at least 1.")
        if not agent_name.strip():
            raise ValueError("agent_name must not be empty.")

        runner = BenchmarkRunner(max_steps=self.max_steps)
        runs = tuple(
            runner.run(suite, agent_factory, agent_name=agent_name)
            for _ in range(repetitions)
        )
        return RepeatedBenchmarkResult(
            suite_id=suite.id,
            suite_version=suite.version,
            agent_name=agent_name,
            runs=runs,
        )
