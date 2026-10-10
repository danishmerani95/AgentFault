import json
from typing import Any

from cartspec.agent import DeterministicCommerceAgent
from cartspec.cli import main
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from cartspec.tools import ToolRegistry
from examples.basic_world import create_basic_world


class _AlwaysFailAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        return AssertionResult(passed=False, message="Intentional failing assertion.")


def build_failing_scenario() -> tuple[Scenario, ToolRegistry]:
    environment = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(environment))
    scenario = Scenario(
        name="intentional failure",
        agent=DeterministicCommerceAgent(query="headphones", max_price=150.0),
        environment=environment,
        assertions=[_AlwaysFailAssertion()],
    )
    return scenario, registry


def test_cli_runs_a_scenario(capsys: Any) -> None:
    exit_code = main(["run", "examples.basic_scenario:build_scenario"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Scenario: headphones within budget" in captured.out
    assert "Result: PASSED" in captured.out


def test_cli_can_emit_json(capsys: Any) -> None:
    exit_code = main(
        ["run", "examples.basic_scenario:build_scenario", "--json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["scenario"] == "headphones within budget"
    assert payload["assertions"][0]["passed"] is True


def test_cli_returns_one_when_assertions_fail(capsys: Any) -> None:
    exit_code = main(["run", "tests.test_cli:build_failing_scenario"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Result: FAILED" in captured.out
    assert "Intentional failing assertion." in captured.out


def test_cli_returns_two_for_invalid_factory(capsys: Any) -> None:
    exit_code = main(["run", "not_a_real_module:nope"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "AgentFault: error:" in captured.err
