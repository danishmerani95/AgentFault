import ast
import inspect

import pytest

import agentfault.testing.runner
import agentfault.testing.scenario
from agentfault.testing import Perturbation, Scenario, ScenarioResult, Trigger
from agentfault.testing.assertion import AssertionResult
from agentfault.testing.perturbations import ChangePrice
from agentfault.testing.triggers import AfterTool
from agentfault.trajectory import TrajectoryStep


def test_scenario_construction() -> None:
    agent = object()
    environment = object()
    trigger = AfterTool(tool_name="get_offers_for_product")
    perturbation = ChangePrice(offer_id="offer_1", new_price=179.0)

    scenario = Scenario(
        name="price changes",
        agent=agent,
        environment=environment,
        perturbations=[(trigger, perturbation)],
    )

    assert scenario.name == "price changes"
    assert scenario.agent is agent
    assert scenario.environment is environment
    assert scenario.perturbations == [(trigger, perturbation)]
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


def test_trigger_is_abstract() -> None:
    with pytest.raises(TypeError):
        Trigger()


def test_agent_runner_remains_generic() -> None:
    module = ast.parse(inspect.getsource(agentfault.testing.runner))
    referenced_names = {
        node.id for node in ast.walk(module) if isinstance(node, ast.Name)
    }

    assert referenced_names.isdisjoint(
        {
            "Scenario",
            "ScenarioRunner",
            "Perturbation",
            "Trigger",
            "Assertion",
            "CommerceEnvironment",
        }
    )


def test_scenario_remains_declarative_and_does_not_own_tool_registry() -> None:
    module = ast.parse(inspect.getsource(agentfault.testing.scenario))
    scenario_definition = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "Scenario"
    )

    assert not any(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for node in scenario_definition.body
    )
    assert "ToolRegistry" not in inspect.getsource(agentfault.testing.scenario)
