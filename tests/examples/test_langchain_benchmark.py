import pytest

from agentfault.tools import Tool


def test_langchain_adapter_executes_one_tool_turn_at_a_time() -> None:
    pytest.importorskip("langchain_core")
    pytest.importorskip("langchain_openai")

    from langchain_core.messages import AIMessage, ToolMessage

    from examples.langchain_benchmark import LangChainToolCallingAgent

    class FakeModel:
        def __init__(self) -> None:
            self.responses = [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "lookup_product",
                            "args": {"query": "headphones"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="Finished safely."),
            ]
            self.invocations: list[list[object]] = []
            self.bound_tools: list[object] = []
            self.parallel_tool_calls: bool | None = None

        def bind_tools(self, tools, *, parallel_tool_calls: bool):
            self.bound_tools = tools
            self.parallel_tool_calls = parallel_tool_calls
            return self

        def invoke(self, messages):
            self.invocations.append(list(messages))
            return self.responses.pop(0)

    def lookup_product(query: str) -> dict[str, str]:
        return {"found": query}

    fake_model = FakeModel()
    agent = LangChainToolCallingAgent(
        model=fake_model,
        task="Find headphones.",
        tools=[
            Tool(
                name="lookup_product",
                description="Look up a product.",
                function=lookup_product,
            )
        ],
    )

    first_action = agent.next_action(None)

    assert first_action is not None
    assert first_action.name == "lookup_product"
    assert first_action.arguments == {"query": "headphones"}
    assert first_action.id == "call-1"
    assert fake_model.parallel_tool_calls is False
    assert len(fake_model.bound_tools) == 1

    assert agent.next_action({"found": "headphones"}) is None

    second_turn = fake_model.invocations[1]
    tool_messages = [message for message in second_turn if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-1"
    assert tool_messages[0].content == '{"found": "headphones"}'
