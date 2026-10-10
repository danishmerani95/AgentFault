import pytest

from agentfault.testing import ScenarioResult


@pytest.mark.agentfault("examples.basic_scenario:build_scenario")
def test_scenario_factory_runs_as_a_pytest_fixture(
    agentfault_result: ScenarioResult,
) -> None:
    assert agentfault_result.passed, [
        assertion.message
        for assertion in agentfault_result.assertions
        if not assertion.passed
    ]
