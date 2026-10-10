from typing import Any

from agentfault.agent import DeterministicCommerceAgent
from agentfault.commerce import create_commerce_tools
from agentfault.testing import AgentRunner, Scenario, ScenarioRunner
from agentfault.tools import Tool, ToolCall, ToolExecutor, ToolRegistry
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

    assert result == {
        "type": "tool_error",
        "tool_name": "failing_tool",
        "error_type": "ValueError",
        "message": "Not enough inventory.",
    }
    assert captured_tool_call is not None
    assert captured_tool_call.name == "failing_tool"

    assert captured_error is not None
    assert isinstance(captured_error, ValueError)
    assert str(captured_error) == "Not enough inventory."

    assert agent.call_count == 2
    assert len(agent_runner.trajectory) == 1
    assert agent_runner.trajectory[0].succeeded is False
    assert agent_runner.trajectory[0].error == {
        "type": "ValueError",
        "message": "Not enough inventory.",
    }


class _FixedExecutor(ToolExecutor):
    def __init__(self) -> None:
        self.calls: list[ToolCall] = []

    def execute(self, tool_call: ToolCall) -> str:
        self.calls.append(tool_call)
        return "executed"


def test_agent_runner_uses_tool_executor_boundary() -> None:
    agent = FailingAgent()
    executor = _FixedExecutor()

    agent_runner = AgentRunner(
        agent=agent,
        tool_executor=executor,
    )

    result = agent_runner.run()

    assert result == "executed"
    assert len(executor.calls) == 1
    assert executor.calls[0].name == "failing_tool"
    assert agent_runner.trajectory[0].observation == "executed"


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

    assert test_result.trajectory[0].succeeded is False
    assert test_result.trajectory[0].error == {
        "type": "ValueError",
        "message": "Not enough inventory.",
    }
    # A completed run is not failed solely because a tool call raised an exception.
    assert test_result.passed is True
    assert test_result.error is None
