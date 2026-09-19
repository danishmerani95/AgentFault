from cartspec.agent.deterministic import DeterministicCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing.assertions.budget import MaxPriceAssertion
from cartspec.testing.test_case import TestCase
from cartspec.testing.test_runner import TestRunner
from cartspec.tools.tool import ToolRegistry
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

    runner = TestRunner(
        agent=agent,
        tool_registry=registry,
    )

    result = runner.run(test_case)

    assert result.passed is True
    assert len(result.assertions) == 1
    assert result.assertions[0].passed is True
