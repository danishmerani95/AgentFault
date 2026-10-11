from openai import OpenAI

from agentfault.integrations.openai import OpenAIAgent, to_openai_tools
from agentfault.tools import Tool
from examples.openai_benchmark import openai_agent_factory


def test_openai_benchmark_factory_is_configurable_without_a_network_call(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGENTFAULT_OPENAI_MODEL", "test-model")

    def lookup_product(query: str) -> str:
        return f"found {query}"

    tools = [
        Tool(
            name="lookup_product",
            description="Look up a product.",
            function=lookup_product,
        )
    ]

    agent = openai_agent_factory("Find an example product.", tools)

    assert isinstance(agent, OpenAIAgent)
    assert isinstance(agent.client, OpenAI)
    assert agent.model == "test-model"
    assert agent.messages[1]["content"] == "Find an example product."
    assert agent.tools == to_openai_tools(tools)
