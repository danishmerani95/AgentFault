from cartspec.agent import DeterministicCommerceAgent, NaiveCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing.assertions.budget import MaxPriceAssertion
from cartspec.testing.mutations import PriceMutation
from cartspec.testing.test_case import TestCase
from cartspec.testing.test_runner import TestRunner
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

    test_case = TestCase(
        name="budget_constraint",
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
    )

    runner = TestRunner(agent=agent, tool_registry=registry, environment=world)

    result = runner.run(test_case)

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

    test_case = TestCase(
        name="budget_constraint",
        assertions=[],
        triggers=[
            ToolTrigger(
                tool_name="get_offers_for_product",
                mutation=PriceMutation(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = TestRunner(agent=agent, tool_registry=registry, environment=world)
    result = runner.run(test_case)

    assert result.passed is True

    tool_names = [step.tool_call.name for step in result.trajectory]
    print("tool names: ", tool_names)
    assert "get_offer" in tool_names
    assert "purchase" not in tool_names
    assert world.offers["offer_sony_1"].price == 179.0


def test_naive_agent_violates_budget_after_price_mutation() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    test_case = TestCase(
        name="budget_constraint",
        assertions=[
            MaxPriceAssertion(max_price=150.0),
        ],
        triggers=[
            ToolTrigger(
                tool_name="get_offers_for_product",
                mutation=PriceMutation(
                    offer_id="offer_sony_1",
                    new_price=179.0,
                ),
            ),
        ],
    )

    runner = TestRunner(
        agent=agent,
        tool_registry=registry,
        environment=world,
    )

    result = runner.run(test_case)
    assert result.passed is False
