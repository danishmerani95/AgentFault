"""Anthropic Messages API adapter with AgentFault model-call fault injection.

The Anthropic SDK is optional: pass a client implementing messages.create.
The adapter uses the generic Agent contract and returns exactly one ToolCall per
model response so AgentFault can execute a tool, apply scenario changes, then
send the resulting observation back to Claude before its next decision.
"""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from agentfault.agent import Agent
from agentfault.testing.faults import ModelCallExecutor
from agentfault.tools import Tool, ToolCall


def to_anthropic_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    """Convert AgentFault tools to the Anthropic Messages API tool schema."""
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


class AnthropicAgent(Agent):
    """A generic Claude tool-calling agent instrumented for model fault tests.

    The `client` can be an `anthropic.Anthropic` instance or a compatible fake
    client. The Anthropic SDK is deliberately not imported by this module.
    Parallel tool-use responses are rejected so environment perturbations can be
    observed by the next model decision instead of racing within one batch.
    """

    def __init__(
        self,
        *,
        client: Any,
        system_prompt: str,
        user_prompt: str,
        tools: list[Tool],
        model: str,
        max_tokens: int = 1024,
        model_call_executor: ModelCallExecutor | None = None,
    ) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")
        self.client = client
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.tools = to_anthropic_tools(tools)
        self.model_call_executor = model_call_executor or ModelCallExecutor()
        self.messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt}
        ]
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
            raise TypeError("Anthropic returned a content block with an unsupported shape.")
        return result

    @staticmethod
    def _get(block: Any, name: str) -> Any:
        return block.get(name) if isinstance(block, dict) else getattr(block, name, None)

    def next_action(self, observation: Any) -> ToolCall | None:
        """Get one model decision and return its tool request, if any."""
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

        response = self.model_call_executor.execute(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=self.messages,
                tools=self.tools,
                tool_choice={
                    "type": "auto",
                    "disable_parallel_tool_use": True,
                },
            )
        )

        if response is None or not hasattr(response, "content"):
            raise ValueError("Anthropic response did not include any content blocks.")
        raw_content = response.content
        if not raw_content:
            raise ValueError("Anthropic response did not include any content blocks.")
        content = list(raw_content)
        tool_uses = [
            block
            for block in content
            if self._get(block, "type") == "tool_use"
        ]
        if len(tool_uses) > 1:
            raise ValueError(
                "AnthropicAgent supports one tool use per response; "
                f"received {len(tool_uses)}."
            )

        self.messages.append(
            {
                "role": "assistant",
                "content": [
                    self._serialize_content_block(block) for block in content
                ],
            }
        )

        if not tool_uses:
            return None

        tool_use = tool_uses[0]
        name = self._get(tool_use, "name")
        arguments = self._get(tool_use, "input")
        tool_use_id = self._get(tool_use, "id")
        if not isinstance(name, str) or not name:
            raise ValueError("Anthropic tool_use block is missing a name.")
        if not isinstance(arguments, dict):
            raise ValueError("Anthropic tool_use input must be a JSON object.")
        if not isinstance(tool_use_id, str) or not tool_use_id:
            raise ValueError("Anthropic tool_use block is missing an id.")

        self._previous_tool_use_id = tool_use_id
        return ToolCall(name=name, arguments=arguments, id=tool_use_id)
