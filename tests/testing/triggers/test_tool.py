from agentfault.testing.triggers import AfterTool, BeforeTool
from agentfault.tools import ToolCall


def test_before_tool_matches_only_its_tool() -> None:
    trigger = BeforeTool(tool_name="get_offers_for_product")

    assert trigger.tool_name == "get_offers_for_product"
    assert trigger.matches(ToolCall(name="get_offers_for_product", arguments={}))
    assert not trigger.matches(ToolCall(name="get_offer", arguments={}))


def test_after_tool_matches_only_its_tool() -> None:
    trigger = AfterTool(tool_name="get_offers_for_product")

    assert trigger.matches(ToolCall(name="get_offers_for_product", arguments={}))
    assert not trigger.matches(ToolCall(name="get_offer", arguments={}))
