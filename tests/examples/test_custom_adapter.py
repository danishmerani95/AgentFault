from agentfault.testing.scenario_runner import ScenarioRunner
from examples.custom_adapter import build_scenario


def test_custom_adapter_can_use_agentfault_scenario_runner() -> None:
    scenario, registry = build_scenario()

    result = ScenarioRunner(registry).run(scenario)

    assert result.passed is True
    assert scenario.environment.account_status == "suspended"
    assert all(assertion.passed for assertion in result.assertions)
    assert not any(
        step.tool_call.name == "issue_refund"
        for step in result.trajectory
    )
