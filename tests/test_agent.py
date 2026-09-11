from cartspec.commerce_tools import create_commerce_tools
from cartspec.deterministic_agent import DeterministicCommerceAgent
from cartspec.runner import AgentRunner
from cartspec.tool import ToolRegistry
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
