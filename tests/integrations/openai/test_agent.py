import json
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import pytest
from openai.types.chat import ChatCompletionMessageFunctionToolCall

from cartspec.integrations.openai.agent import OpenAIAgent, OpenAICommerceAgent
from cartspec.tools import ToolCall


class _FakeCompletions:
    def __init__(
        self,
        responses: Iterable[Any] = (),
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses)
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)


class _FakeClient:
    def __init__(
        self,
        responses: Iterable[Any] = (),
        error: Exception | None = None,
    ) -> None:
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(responses=responses, error=error)
        )


def _response(*tool_calls: Any) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(tool_calls=list(tool_calls) or None)
            )
        ]
    )


def _tool_call(
    *,
    call_id: str = "call_1",
    name: str = "search_products",
    arguments: str = '{"query": "headphones"}',
) -> ChatCompletionMessageFunctionToolCall:
    return ChatCompletionMessageFunctionToolCall(
        id=call_id,
        type="function",
        function={
            "name": name,
            "arguments": arguments,
        },
    )


def _agent(client: _FakeClient) -> OpenAICommerceAgent:
    agent = OpenAICommerceAgent(
        query="headphones",
        max_price=150.0,
        tools=[],
        model="test-model",
    )
    agent.client = client
    return agent


@pytest.fixture(autouse=True)
def _openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_valid_single_tool_call_becomes_generic_tool_call() -> None:
    client = _FakeClient([_response(_tool_call())])
    agent = _agent(client)

    action = agent.next_action(None)

    assert action == ToolCall(
        id="call_1",
        name="search_products",
        arguments={"query": "headphones"},
    )


def test_assistant_and_tool_messages_are_ordered_across_calls() -> None:
    client = _FakeClient(
        [
            _response(_tool_call(call_id="call_1")),
            _response(_tool_call(call_id="call_2", name="create_cart")),
        ]
    )
    agent = _agent(client)

    agent.next_action(None)
    agent.next_action({"products": ["sony_wh1000xm5"]})

    roles = [message["role"] for message in agent.messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert agent.messages[2]["tool_calls"][0]["id"] == "call_1"  # type: ignore[index]
    assert agent.messages[3]["tool_call_id"] == "call_1"  # type: ignore[index]
    assert agent.messages[4]["tool_calls"][0]["id"] == "call_2"  # type: ignore[index]


def test_response_with_no_tool_calls_returns_none() -> None:
    client = _FakeClient([_response()])
    agent = _agent(client)

    assert agent.next_action(None) is None


def test_none_tool_result_is_serialized_and_appended() -> None:
    client = _FakeClient([_response(_tool_call()), _response()])
    agent = _agent(client)

    agent.next_action(None)
    assert agent.next_action(None) is None

    assert agent.messages[-1]["role"] == "tool"
    assert agent.messages[-1]["tool_call_id"] == "call_1"  # type: ignore[index]
    assert agent.messages[-1]["content"] == "null"  # type: ignore[index]


def test_malformed_json_arguments_raise_clear_error_without_history_mutation() -> None:
    client = _FakeClient([_response(_tool_call(arguments="{not json"))])
    agent = _agent(client)

    with pytest.raises(ValueError, match="valid JSON"):
        agent.next_action(None)

    assert [message["role"] for message in agent.messages] == ["system", "user"]


def test_multiple_tool_calls_are_rejected_without_history_mutation() -> None:
    client = _FakeClient(
        [
            _response(
                _tool_call(call_id="call_1"),
                _tool_call(call_id="call_2", name="create_cart"),
            )
        ]
    )
    agent = _agent(client)

    with pytest.raises(ValueError, match="supports one tool call per response"):
        agent.next_action(None)

    assert [message["role"] for message in agent.messages] == ["system", "user"]


def test_unexpected_tool_call_type_raises_clear_error() -> None:
    client = _FakeClient([_response(SimpleNamespace(type="custom"))])
    agent = _agent(client)

    with pytest.raises(TypeError, match="Expected a function tool call"):
        agent.next_action(None)


def test_malformed_response_structure_raises_clear_error() -> None:
    client = _FakeClient([SimpleNamespace(choices=[])])
    agent = _agent(client)

    with pytest.raises(ValueError, match="did not include any choices"):
        agent.next_action(None)


def test_provider_exceptions_propagate() -> None:
    error = RuntimeError("provider failed")
    client = _FakeClient(error=error)
    agent = _agent(client)

    with pytest.raises(RuntimeError, match="provider failed"):
        agent.next_action(None)

def test_tool_error_observation_is_sent_as_tool_result_json() -> None:
    client = _FakeClient([_response(_tool_call()), _response()])
    agent = _agent(client)
    agent.next_action(None)

    error_observation = {
        "type": "tool_error",
        "tool_name": "search_products",
        "error_type": "RuntimeError",
        "message": "temporary failure",
    }
    assert agent.next_action(error_observation) is None

    tool_message = agent.messages[-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_1"  # type: ignore[index]
    assert json.loads(tool_message["content"]) == error_observation  # type: ignore[index]



def test_generic_openai_agent_uses_supplied_prompts_and_tool_schemas() -> None:
    client = _FakeClient([_response(_tool_call(name="read_document"))])
    agent = OpenAIAgent(
        system_prompt="You help users analyze documents.",
        user_prompt="Summarize the quarterly report.",
        tools=[],
        model="test-model",
        client=client,  # type: ignore[arg-type]
    )

    action = agent.next_action(None)

    assert action is not None
    assert action.name == "read_document"
    request_messages = client.chat.completions.calls[0]["messages"]
    assert request_messages[0]["role"] == "system"
    assert request_messages[0]["content"] == "You help users analyze documents."
    assert request_messages[1]["role"] == "user"
    assert request_messages[1]["content"] == "Summarize the quarterly report."


def test_commerce_agent_remains_a_compatible_prompt_wrapper() -> None:
    client = _FakeClient([_response(_tool_call())])
    agent = OpenAICommerceAgent(
        query="headphones",
        max_price=150.0,
        tools=[],
        model="test-model",
        client=client,  # type: ignore[arg-type]
    )

    agent.next_action(None)

    request_messages = client.chat.completions.calls[0]["messages"]
    assert request_messages[0]["content"].startswith("You are a commerce agent.")
    assert request_messages[1]["content"] == "Buy me headphones under 150.0 EUR."
    assert agent.query == "headphones"
    assert agent.max_price == 150.0
