from cartspec.agent import Agent
from cartspec.testing.assertion import AssertionResult
from cartspec.testing.runner import AgentRunner
from cartspec.testing.test_case import TestCase
from cartspec.testing.test_result import TestResult
from cartspec.tools.tool import ToolRegistry


class TestRunner:
    __test__ = False

    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
    ) -> None:
        self.agent = agent
        self.tool_registry = tool_registry

    def run(self, test_case: TestCase) -> TestResult:
        agent_runner = AgentRunner(
            agent=self.agent,
            tool_registry=self.tool_registry,
        )

        result = agent_runner.run()

        assertion_results: list[AssertionResult] = [
            assertion.check(
                result=result,
                trajectory=agent_runner.trajectory,
            )
            for assertion in test_case.assertions
        ]

        passed = all(assertion_result.passed for assertion_result in assertion_results)

        return TestResult(
            passed=passed,
            assertions=assertion_results,
            trajectory=agent_runner.trajectory,
        )
