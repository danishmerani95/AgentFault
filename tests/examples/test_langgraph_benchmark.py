from typing import Any

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")


from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkCase, BenchmarkRunner, BenchmarkSuite
from agentfault.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from agentfault.tools import Tool, ToolRegistry


class FakeModel:
    def __init__(self) -> None:
        self.calls = 0
        self.bound_tools: list[Any] = []

    def bind_tools(self, tools, *, parallel_tool_calls: bool):
        assert parallel_tool_calls is False
        self.bound_tools = list(tools)
        return self

    def invoke(self, messages):
        from langchain_core.messages import AIMessage, ToolMessage

        self.calls += 1
        if not any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "lookup",
                        "args": {},
                        "id": "call-lookup-1",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content="Lookup completed safely.")


class LookupAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        passed = context.environment["lookups"] == 1
        return AssertionResult(passed, f"lookup count is {context.environment['lookups']}")


def test_langgraph_can_execute_benchmark_case_with_native_tool_node(monkeypatch) -> None:
    import examples.langgraph_benchmark as example

    model = FakeModel()
    monkeypatch.setattr(example, "create_chat_model", lambda: model)

    def build_case(agent_factory) -> tuple[Scenario, ToolRegistry]:
        world = {"lookups": 0}

        def lookup() -> dict[str, str]:
            world["lookups"] += 1
            return {"status": "ok"}

        tools = [Tool("lookup", "Look up the test record.", lookup)]
        scenario = Scenario(
            name="graph executes the tool",
            agent=agent_factory("Look up the test record.", tools),
            environment=world,
            assertions=[LookupAssertion()],
        )
        return scenario, ToolRegistry(tools)

    suite = BenchmarkSuite(
        id="langgraph-native-test",
        version="1.0.0",
        category="testing",
        description="Ensure framework-native benchmark execution works.",
        cases=(BenchmarkCase("LG-001", "Run one tool", build_case),),
    )
    result = BenchmarkRunner(max_steps=4).run(
        suite,
        example.langgraph_agent_factory,
        agent_name="fixture-langgraph",
        scenario_executor=example.langgraph_scenario_executor,
    )

    assert result.complete
    assert result.score == 100.0
    scenario_result = result.cases[0].scenario_result
    assert scenario_result is not None
    assert [step.tool_call.name for step in scenario_result.trajectory] == ["lookup"]
    assert scenario_result.trajectory[0].succeeded is True
    assert all(assertion.passed for assertion in scenario_result.assertions)
