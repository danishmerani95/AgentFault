from cartspec.agent import Agent
from cartspec.commerce.environment import CommerceEnvironment
from cartspec.testing.assertion import AssertionResult
from cartspec.testing.mutations.base import Mutation
from cartspec.testing.runner import AgentRunner
from cartspec.testing.test_case import TestCase
from cartspec.testing.test_result import TestResult
from cartspec.tools.tool import ToolCall, ToolRegistry


class TestRunner:
    __test__ = False

    def __init__(
        self,
        agent: Agent,
        tool_registry: ToolRegistry,
        environment: CommerceEnvironment,
    ) -> None:
        self.agent = agent
        self.tool_registry = tool_registry
        self.pending_mutations: list[Mutation] = []
        self.environment = environment

    def run(self, test_case: TestCase) -> TestResult:
        agent_runner = AgentRunner(
            agent=self.agent,
            tool_registry=self.tool_registry,
            before_tool_execution=self._before_tool_executed,
            on_tool_executed=lambda tool_call, _: self._on_tool_executed(
                test_case, tool_call
            ),
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

    def _before_tool_executed(self, _: ToolCall) -> None:
        for mutation in self.pending_mutations:
            mutation.apply(self.environment)

        self.pending_mutations = []

    def _on_tool_executed(self, test_case: TestCase, tool_call: ToolCall) -> None:
        for trigger in test_case.triggers:
            if trigger.tool_name == tool_call.name:
                self.pending_mutations.append(trigger.mutation)
