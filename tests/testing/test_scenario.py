import pytest

from cartspec.testing import Perturbation, Scenario, ScenarioResult
from cartspec.testing.assertion import AssertionResult
from cartspec.testing.perturbations import PriceMutation
from cartspec.testing.triggers import ToolTrigger
from cartspec.trajectory import TrajectoryStep


def test_scenario_construction() -> None:
    agent = object()
    environment = object()
    perturbation = PriceMutation(offer_id="offer_1", new_price=179.0)
    trigger = ToolTrigger(tool_name="get_offers_for_product", perturbation=perturbation)

    scenario = Scenario(
        name="price changes",
        agent=agent,
        environment=environment,
        perturbations=[trigger],
    )

    assert scenario.name == "price changes"
    assert scenario.agent is agent
    assert scenario.environment is environment
    assert scenario.perturbations == [trigger]
    assert scenario.assertions == []


def test_scenario_result_construction() -> None:
    assertion = AssertionResult(passed=True, message="within budget")
    trajectory_step = TrajectoryStep(tool_call=object(), observation="completed")

    result = ScenarioResult(
        passed=True,
        assertions=[assertion],
        trajectory=[trajectory_step],
    )

    assert result.passed is True
    assert result.assertions == [assertion]
    assert result.trajectory == [trajectory_step]
    assert result.error is None


def test_perturbation_is_abstract() -> None:
    with pytest.raises(TypeError):
        Perturbation()
