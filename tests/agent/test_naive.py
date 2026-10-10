from typing import Any

from agentfault.agent.naive import NaiveCommerceAgent
from agentfault.commerce.tools import create_commerce_tools
from agentfault.tools.tool import ToolRegistry
from examples.basic_world import create_basic_world


def test_naive_agent_follows_happy_path() -> None:
    world = create_basic_world()
    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = NaiveCommerceAgent(query="headphones")

    observation: Any = None
    tool_names: list[str] = []

    while True:
        tool_call = agent.next_action(observation)

        if tool_call is None:
            break

        tool_names.append(tool_call.name)
        observation = registry.execute(tool_call)

    assert tool_names == [
        "search_products",
        "get_offers_for_product",
        "create_cart",
        "add_to_cart",
        "purchase",
    ]
