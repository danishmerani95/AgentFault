from agentfault.testing import ScenarioRunner
from examples.scenarios.state_change import build_scenario as build_state_change
from examples.scenarios.tool_failure_recovery import (
    build_scenario as build_tool_failure_recovery,
)
from examples.scenarios.unsafe_purchase import build_scenario as build_unsafe_purchase


def test_state_change_scenario_passes_without_adding_or_purchasing() -> None:
    scenario, registry = build_state_change()

    result = ScenarioRunner(registry).run(scenario)

    assert result.passed is True
    assert all(assertion.passed for assertion in result.assertions)
    assert scenario.environment.inventories["offer_sony_1"].quantity == 0
    assert not any(
        step.tool_call.name in {"add_to_cart", "purchase"}
        for step in result.trajectory
    )


def test_tool_failure_scenario_passes_after_successful_retry() -> None:
    scenario, registry = build_tool_failure_recovery()

    result = ScenarioRunner(registry).run(scenario)

    assert result.passed is True
    assert result.error is None
    create_cart_steps = [
        step for step in result.trajectory
        if step.tool_call.name == "create_cart"
    ]
    assert [step.succeeded for step in create_cart_steps] == [False, True]
    assert len(scenario.environment.carts) == 1


def test_unsafe_purchase_scenario_fails_with_over_budget_order() -> None:
    scenario, registry = build_unsafe_purchase()

    result = ScenarioRunner(registry).run(scenario)

    assert result.passed is False
    assert [assertion.passed for assertion in result.assertions] == [False, False]
    orders = list(scenario.environment.orders.values())
    assert len(orders) == 1
    assert orders[0].total_price == 179.0
