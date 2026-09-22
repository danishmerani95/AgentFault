from typing import Any

from cartspec.agent.deterministic import DeterministicCommerceAgent
from cartspec.commerce.tools import create_commerce_tools
from cartspec.testing.runner import AgentRunner
from cartspec.tools.tool import ToolCall, ToolRegistry
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


def test_received_tool_call_and_observations() -> None:
    mock_tool_call_list: list[ToolCall] = []
    mock_observation_list: list[Any] = []

    def on_tool_executed(toolCall: ToolCall, observation: Any) -> None:
        mock_tool_call_list.append(toolCall)
        mock_observation_list.append(observation)

    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    agent = DeterministicCommerceAgent(
        query="headphones",
        max_price=150.0,
    )

    runner = AgentRunner(
        agent=agent, tool_registry=registry, on_tool_executed=on_tool_executed
    )

    runner.run()

    assert len(mock_tool_call_list) > 0
    assert len(mock_observation_list) > 0
    assert len(mock_tool_call_list) == len(mock_observation_list)

    first_tool_call = mock_tool_call_list[0]
    first_observation = mock_observation_list[0]

    assert first_tool_call.name == "search_products"
    assert first_observation is not None


def test_hook_order_is_correct() -> None:
    events = []

    def before_tool_call_executed(toolCall: ToolCall) -> None:
        events.append(f"before:{toolCall.name}")

    def on_tool_executed(toolCall: ToolCall, observation: Any) -> None:
        events.append(f"after:{toolCall.name}")

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
        before_tool_execution=before_tool_call_executed,
        on_tool_executed=on_tool_executed,
    )

    runner.run()

    assert events[0] == "before:search_products"
    assert events[1] == "after:search_products"
