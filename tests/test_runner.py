from cartspec.commerce_tools import create_commerce_tools
from cartspec.deterministic_agent import DeterministicCommerceAgent
from cartspec.runner import AgentRunner
from cartspec.tool import ToolRegistry
from examples.basic_world import create_basic_world


def test_runner_preserves_observation_snapshot() -> None:
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

    add_to_cart_step = runner.trajectory[5]

    assert len(add_to_cart_step.observation.items) == 1
    assert add_to_cart_step.observation.items[0].offer_id == "offer_sony_1"
