from cartspec.commerce.tools import create_commerce_tools
from cartspec.tools.tool import ToolCall, ToolRegistry
from examples.basic_world import create_basic_world


def test_tool_call_execution() -> None:
    world = create_basic_world()

    tools = create_commerce_tools(world)
    registry = ToolRegistry(tools)

    tool_call = ToolCall(
        name="search_products",
        arguments={"query": "headphones"},
    )

    result = registry.execute(tool_call)

    assert len(result) == 1
    assert result[0].name == "Sony WH-1000XM5"
