from agentfault.agent import DeterministicCommerceAgent
from agentfault.commerce.tools import create_commerce_tools
from agentfault.testing.runner import AgentRunner
from agentfault.tools.tool import ToolRegistry
from examples.basic_world import create_basic_world


def test_deterministic_agent_can_purchase() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    runner = AgentRunner(
        agent=agent,
        tool_registry=registry,
    )

    orders = runner.run()

    assert len(orders) == 1
    assert orders[0].total_price == 139.0
    assert orders[0].status == "completed"

    assert world.inventories["offer_sony_1"].quantity == 4


def test_deterministic_agent_records_trajectory() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    runner = AgentRunner(
        agent=agent,
        tool_registry=registry,
    )

    runner.run()

    tool_names = [step.tool_call.name for step in runner.trajectory]

    assert tool_names == [
        "search_products",
        "get_offers_for_product",
        "get_offer",
        "check_inventory",
        "create_cart",
        "add_to_cart",
        "purchase",
    ]
