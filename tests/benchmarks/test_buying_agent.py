from agentfault.agent import DeterministicCommerceAgent, NaiveCommerceAgent
from agentfault.benchmarks import BenchmarkRunner
from agentfault.benchmarks.packs import buying_agent_v1
from agentfault.tools import Tool


def robust_agent(task: str, tools: list[Tool]) -> DeterministicCommerceAgent:
    return DeterministicCommerceAgent(query="headphones", max_price=150.0)


def naive_agent(task: str, tools: list[Tool]) -> NaiveCommerceAgent:
    return NaiveCommerceAgent(query="headphones")


def test_robust_reference_agent_passes_buying_benchmark() -> None:
    result = BenchmarkRunner().run(buying_agent_v1(), robust_agent)

    assert result.complete
    assert result.score == 100.0
    assert [case.status for case in result.cases] == ["passed"] * 5


def test_naive_agent_is_caught_by_stateful_buying_cases() -> None:
    result = BenchmarkRunner().run(buying_agent_v1(), naive_agent)

    assert result.complete
    assert result.score is not None
    assert result.score < 100.0
    assert result.cases[0].status == "passed"
    assert any(case.status == "failed" for case in result.cases[1:])


def test_buying_result_contains_scenario_evidence() -> None:
    result = BenchmarkRunner().run(buying_agent_v1(), robust_agent)
    payload = result.to_dict()

    assert payload["suite_id"] == "buying-agent"
    assert payload["suite_version"] == "1.0.0"
    assert payload["score"] == 100.0
    cases = payload["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 5
    first_case = cases[0]
    assert isinstance(first_case, dict)
    assert first_case["status"] == "passed"
    assert first_case["assertions"]
    assert first_case["tool_calls"]
