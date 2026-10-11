"""Run any Agent Fault domain benchmark with an Anthropic Claude tool-calling agent.

From the repository root:
    export ANTHROPIC_API_KEY=...
    export AGENTFAULT_BENCHMARK_SUITE=customer-support-agent
    uv run --with "anthropic>=0.50,<1" python -m examples.claude_benchmark

The tools are always bound to each suite's synthetic fixture environment.
"""

import json
import os
from dataclasses import asdict, is_dataclass
from typing import Any

from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkRunner
from agentfault.tools import Tool, ToolCall
from examples.benchmark_suites import GENERAL_AGENT_SYSTEM_PROMPT, load_benchmark_suite


def to_claude_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    """Convert AgentFault tools into Anthropic Messages API tool schemas."""
    converted: list[dict[str, Any]] = []
    for tool in tools:
        function_schema = tool.to_openai_schema()["function"]
        converted.append(
            {
                "name": function_schema["name"],
                "description": function_schema["description"],
                "input_schema": function_schema["parameters"],
            }
        )
    return converted


class ClaudeToolCallingAgent(Agent):
    """Adapt Claude tool use to AgentFault's one-tool-at-a-time Agent contract.

    AgentFault executes the returned ToolCall through the registered synthetic
    tool, then passes the result back as a Claude tool_result block. This makes
    scenario changes visible to the next model decision.
    """

    def __init__(
        self,
        *,
        client: Any,
        task: str,
        tools: list[Tool],
        model: str,
        max_tokens: int = 1024,
    ) -> None:
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.tools = to_claude_tools(tools)
        self.messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        self._previous_tool_use_id: str | None = None

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
        if hasattr(value, "__dict__"):
            return value.__dict__
        return str(value)

    @classmethod
    def _serialize_observation(cls, observation: Any) -> str:
        return json.dumps(observation, default=cls._json_default)

    @classmethod
    def _serialize_content_block(cls, block: Any) -> dict[str, Any]:
        if isinstance(block, dict):
            return block
        if hasattr(block, "model_dump"):
            return block.model_dump(exclude_none=True)
        result: dict[str, Any] = {}
        for key in ("type", "id", "name", "input", "text", "thinking", "signature"):
            if hasattr(block, key):
                result[key] = getattr(block, key)
        if not result:
            raise TypeError("Claude returned a content block with an unsupported shape.")
        return result

    def next_action(self, observation: Any) -> ToolCall | None:
        if self._previous_tool_use_id is not None:
            self.messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": self._previous_tool_use_id,
                            "content": self._serialize_observation(observation),
                        }
                    ],
                }
            )
            self._previous_tool_use_id = None

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=GENERAL_AGENT_SYSTEM_PROMPT,
            messages=self.messages,
            tools=self.tools,
            tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        )
        content = list(response.content)
        self.messages.append(
            {
                "role": "assistant",
                "content": [self._serialize_content_block(block) for block in content],
            }
        )
        tool_uses = [
            block
            for block in content
            if getattr(block, "type", None) == "tool_use"
            or (isinstance(block, dict) and block.get("type") == "tool_use")
        ]
        if not tool_uses:
            return None
        if len(tool_uses) != 1:
            raise ValueError(
                "ClaudeToolCallingAgent supports one tool use per response; "
                f"received {len(tool_uses)}."
            )

        tool_use = tool_uses[0]
        getter = tool_use.get if isinstance(tool_use, dict) else lambda key: getattr(tool_use, key, None)
        name = getter("name")
        arguments = getter("input")
        tool_use_id = getter("id")
        if not isinstance(name, str) or not name:
            raise ValueError("Claude tool_use block is missing a name.")
        if not isinstance(arguments, dict):
            raise ValueError("Claude tool_use input must be a JSON object.")
        if not isinstance(tool_use_id, str) or not tool_use_id:
            raise ValueError("Claude tool_use block is missing an id.")

        self._previous_tool_use_id = tool_use_id
        return ToolCall(name=name, arguments=arguments, id=tool_use_id)


def claude_agent_factory(task: str, tools: list[Tool]) -> Agent:
    """Create a new Claude-backed agent for one benchmark case."""
    try:
        import anthropic
    except ImportError as error:
        raise RuntimeError(
            "Install the Anthropic SDK to run this example: "
            'uv run --with "anthropic>=0.50,<1" python -m examples.claude_benchmark'
        ) from error
    return ClaudeToolCallingAgent(
        client=anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]),
        task=task,
        tools=tools,
        model=os.getenv("AGENTFAULT_CLAUDE_MODEL", "claude-sonnet-4-5"),
    )


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Set ANTHROPIC_API_KEY to run the Claude benchmark.")
    suite_id = os.getenv("AGENTFAULT_BENCHMARK_SUITE", "buying-agent")
    suite = load_benchmark_suite(suite_id)
    model = os.getenv("AGENTFAULT_CLAUDE_MODEL", "claude-sonnet-4-5")
    result = BenchmarkRunner(max_steps=20).run(
        suite,
        claude_agent_factory,
        agent_name=f"claude:{model}",
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
