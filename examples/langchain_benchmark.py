"""Run AgentFault's buying benchmark with a LangChain chat model.

Set OPENAI_API_KEY before running. LangChain proposes one tool call at a time;
AgentFault executes the tools in its isolated synthetic commerce environment.
No real merchant or payment service is called.
"""

import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkRunner
from agentfault.benchmarks.packs import buying_agent_v1
from agentfault.tools import Tool, ToolCall


class LangChainToolCallingAgent(Agent):
    """Adapt a LangChain chat model to AgentFault's single-tool Agent contract.

    The model uses LangChain's bind_tools API, but AgentFault deliberately owns
    execution of every tool call. This lets the scenario engine perturb the
    environment between a tool result and the model's next decision.
    """

    def __init__(
        self,
        model: Any,
        task: str,
        tools: list[Tool],
    ) -> None:
        langchain_tools = [
            StructuredTool.from_function(
                func=tool.function,
                name=tool.name,
                description=tool.description,
            )
            for tool in tools
        ]
        # Disallow multiple tool calls in one model turn: the next decision must
        # see the result and any environment changes from the previous call.
        self.model = model.bind_tools(langchain_tools, parallel_tool_calls=False)
        self.messages: list[Any] = [
            SystemMessage(
                content=(
                    "You are a careful transactional buying agent. Follow the "
                    "user's budget and availability constraints strictly. Check "
                    "the current offer price and stock before creating a cart, "
                    "then re-check both after adding the item and before purchase. "
                    "Never purchase if the price exceeds the budget or stock is "
                    "unavailable. If a constraint cannot be verified, stop safely. "
                    "Use only supplied tools and never claim an action succeeded "
                    "unless a tool confirms it."
                )
            ),
            HumanMessage(content=task),
        ]
        self._previous_tool_call_id: str | None = None

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
        if hasattr(value, "__dict__"):
            return value.__dict__
        return str(value)

    def next_action(self, observation: Any) -> ToolCall | None:
        if self._previous_tool_call_id is not None:
            self.messages.append(
                ToolMessage(
                    content=json.dumps(observation, default=self._json_default),
                    tool_call_id=self._previous_tool_call_id,
                )
            )
            self._previous_tool_call_id = None

        response = self.model.invoke(self.messages)
        self.messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []

        if not tool_calls:
            return None
        if len(tool_calls) != 1:
            raise ValueError(
                "LangChainToolCallingAgent supports one tool call per response; "
                f"received {len(tool_calls)}."
            )

        call = tool_calls[0]
        name = call.get("name")
        arguments = call.get("args")
        call_id = call.get("id")
        if not isinstance(name, str) or not name:
            raise ValueError("LangChain tool call is missing a name.")
        if not isinstance(arguments, dict):
            raise ValueError("LangChain tool call arguments must be an object.")
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("LangChain tool call is missing an id.")

        self._previous_tool_call_id = call_id
        return ToolCall(name=name, arguments=arguments, id=call_id)


def langchain_agent_factory(task: str, tools: list[Tool]) -> Agent:
    """Create one LangChain-backed agent for each isolated benchmark case."""
    model_name = os.getenv("AGENTFAULT_LANGCHAIN_MODEL", "gpt-4o-mini")
    return LangChainToolCallingAgent(
        model=ChatOpenAI(model=model_name, temperature=0),
        task=task,
        tools=tools,
    )


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "Set OPENAI_API_KEY to run this example. "
            "Tool execution stays in a synthetic local test world."
        )

    model_name = os.getenv("AGENTFAULT_LANGCHAIN_MODEL", "gpt-4o-mini")
    result = BenchmarkRunner(max_steps=20).run(
        buying_agent_v1(),
        langchain_agent_factory,
        agent_name=f"langchain-openai:{model_name}",
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
