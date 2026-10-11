from agentfault.benchmarks.models import (
    AgentFactory,
    BenchmarkCaseResult,
    BenchmarkResult,
    BenchmarkSuite,
)
from agentfault.testing import ScenarioRunner


class BenchmarkRunner:
    """Run a versioned benchmark suite against an AgentFault-compatible agent."""

    def __init__(self, max_steps: int = 100) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        self.max_steps = max_steps

    def run(
        self,
        suite: BenchmarkSuite,
        agent_factory: AgentFactory,
        *,
        agent_name: str = "custom-agent",
    ) -> BenchmarkResult:
        """Run all cases with fresh agent/environment instances.

        The factory receives the case task and the exact tools for its isolated
        environment. It must return a new Agent-compatible instance each time.
        """
        if not agent_name.strip():
            raise ValueError("agent_name must not be empty.")

        results: list[BenchmarkCaseResult] = []

        for case in suite.cases:
            try:
                scenario, registry = case.build(agent_factory)
                scenario_result = ScenarioRunner(
                    registry,
                    max_steps=self.max_steps,
                ).run(scenario)
            except Exception as error:
                results.append(
                    BenchmarkCaseResult(
                        case_id=case.id,
                        title=case.title,
                        status="error",
                        error=f"{type(error).__name__}: {error}",
                    )
                )
                continue

            if scenario_result.error is not None:
                status = "error"
                error_message = (
                    f"{type(scenario_result.error).__name__}: "
                    f"{scenario_result.error}"
                )
            elif scenario_result.passed:
                status = "passed"
                error_message = None
            else:
                status = "failed"
                error_message = None

            results.append(
                BenchmarkCaseResult(
                    case_id=case.id,
                    title=case.title,
                    status=status,
                    scenario_result=scenario_result,
                    error=error_message,
                )
            )

        return BenchmarkResult(
            suite_id=suite.id,
            suite_version=suite.version,
            category=suite.category,
            agent_name=agent_name,
            cases=tuple(results),
        )
