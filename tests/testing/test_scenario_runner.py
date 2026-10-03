from cartspec.agent import DeterministicCommerceAgent, NaiveCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing.assertions.budget import MaxPriceAssertion
from cartspec.testing.perturbations import InventoryMutation, PriceMutation
from cartspec.testing.scenario import Scenario
from cartspec.testing.scenario_runner import ScenarioRunner
from cartspec.testing.triggers import ToolTrigger
from cartspec.tools import ToolRegistry
from examples.basic_world import create_basic_world


def test_budget_constraint_passes() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)

    assert result.passed is True
    assert len(result.assertions) == 1
    assert result.assertions[0].passed is True


def test_agent_revalidates_price_after_price_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[],
        perturbations=[
            ToolTrigger(
                tool_name="get_offers_for_product",
                perturbation=PriceMutation(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)
    result = runner.run(scenario)

    assert result.passed is True

    tool_names = [step.tool_call.name for step in result.trajectory]
    offer_observation = result.trajectory[1].observation
    assert offer_observation[0].price == 139.0
    assert "get_offer" in tool_names
    assert "purchase" not in tool_names
    assert world.offers["offer_sony_1"].price == 179.0


def test_naive_agent_violates_budget_after_price_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    scenario = Scenario(
        name="budget_constraint",
        agent=agent,
        environment=world,
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
        perturbations=[
            ToolTrigger(
                tool_name="get_offers_for_product",
                perturbation=PriceMutation(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)
    assert result.passed is False


def test_naive_agent_fails_purchase_after_inventory_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    scenario = Scenario(
        name="quantity_constraint",
        agent=agent,
        environment=world,
        assertions=[],
        perturbations=[
            ToolTrigger(
                tool_name="get_offers_for_product",
                perturbation=InventoryMutation(
                    offer_id="offer_sony_1",
                    new_quantity=0,
                ),
            ),
        ],
    )

    runner = ScenarioRunner(tool_registry=registry)

    result = runner.run(scenario)
    assert result.passed is False
