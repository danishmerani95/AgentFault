from typing import Any

from cartspec.agent import DeterministicCommerceAgent
from cartspec.commerce import create_commerce_tools
from cartspec.testing import AgentRunner, Scenario, ScenarioRunner
from cartspec.tools import Tool, ToolCall, ToolRegistry
from examples.basic_world import create_basic_world
from tests.testing.triggers.mocks import FailingAgent


def test_agent_runner_preserves_observation_snapshot() -> None:
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


def _failing_tool() -> None:
    raise ValueError("Not enough inventory.")


def test_agent_runner_handles_tool_error() -> None:
    agent = FailingAgent()

    tool = Tool(
        name="failing_tool",
        description="A tool that always fails.",
        function=_failing_tool,
    )

    tool_registry = ToolRegistry([tool])
    _ = create_basic_world()

    captured_tool_call: ToolCall | None = None
    captured_error: Exception | None = None

    def on_tool_error(tool_call: ToolCall, error: Exception) -> None:
        nonlocal captured_tool_call
        nonlocal captured_error

        captured_tool_call = tool_call
        captured_error = error

    agent_runner = AgentRunner(
        agent=agent,
        tool_registry=tool_registry,
        on_tool_error=on_tool_error,
    )

    result = agent_runner.run()

    assert result is None
    assert captured_tool_call is not None
    assert captured_tool_call.name == "failing_tool"

    assert captured_error is not None
    assert isinstance(captured_error, ValueError)
    assert str(captured_error) == "Not enough inventory."

    assert agent.call_count == 1
    assert agent_runner.trajectory == []


def test_scenario_runner_captures_tool_execution_failure() -> None:
    agent = FailingAgent()

    environment = create_basic_world()
    tool = Tool(
        name="failing_tool",
        description="A tool that always fails.",
        function=_failing_tool,
    )

    tool_registry = ToolRegistry([tool])

    scenario_runner = ScenarioRunner(tool_registry=tool_registry)

    scenario = Scenario(name="failing tool test", agent=agent, environment=environment)
    test_result = scenario_runner.run(scenario)

    assert test_result.trajectory == []
    assert test_result.passed is False

    assert test_result.error is not None
    assert isinstance(test_result.error, ValueError)
    assert str(test_result.error) == "Not enough inventory."
