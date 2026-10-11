from types import SimpleNamespace
from typing import Any

from agentfault.tools import Tool
from examples.claude_benchmark import ClaudeToolCallingAgent, to_claude_tools


class FakeMessages:
    def __init__(self) -> None:
        self.responses = [
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        id="toolu_test_1",
                        name="lookup",
                        input={"query": "agent reliability"},
                    )
                ]
            ),
            SimpleNamespace(content=[SimpleNamespace(type="text", text="Done.")]),
        ]
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClaudeClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def lookup(query: str) -> dict[str, str]:
    return {"found": query}


def test_claude_adapter_returns_tool_call_and_round_trips_tool_result() -> None:
    client = FakeClaudeClient()
    tools = [
        Tool(name="lookup", description="Look up a research source.", function=lookup)
    ]
    agent = ClaudeToolCallingAgent(
        client=client,
        task="Look up agent reliability.",
        tools=tools,
        model="fixture-model",
    )

    call = agent.next_action(None)

    assert call is not None
    assert call.name == "lookup"
    assert call.arguments == {"query": "agent reliability"}
    assert call.id == "toolu_test_1"

    assert agent.next_action({"found": "agent reliability"}) is None
    second_request = client.messages.calls[1]
    tool_results = [
        block
        for message in second_request["messages"]
        if isinstance(message.get("content"), list)
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]
    assert tool_results == [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_test_1",
            "content": '{"found": "agent reliability"}',
        }
    ]


def test_to_claude_tools_converts_schema_to_input_schema() -> None:
    schema = to_claude_tools(
        [Tool(name="lookup", description="Look up a value.", function=lookup)]
    )

    assert schema[0]["name"] == "lookup"
    assert schema[0]["input_schema"]["type"] == "object"
    assert schema[0]["input_schema"]["properties"]["query"]["type"] == "string"
