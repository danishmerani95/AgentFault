import json
import os
from typing import Any

from pydantic import BaseModel

from agentfault.agent import Agent
from agentfault.testing.faults import ModelCallExecutor
from agentfault.tools.tool import ToolCall
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)


class OpenAIAgent(Agent):
    """Generic OpenAI tool-calling agent driven by caller-supplied prompts."""

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ChatCompletionToolParam],
        model: str,
        client: OpenAI | None = None,
        model_call_executor: ModelCallExecutor | None = None,
    ) -> None:
        self.client = (
            client if client is not None else OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        )
        self.model = model
        self.tools = tools
        self.model_call_executor = model_call_executor or ModelCallExecutor()
        self.messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            ChatCompletionUserMessageParam(role="user", content=user_prompt),
        ]
        self.previous_tool_call_id: str | None = None
        self._awaiting_tool_result = False

    @staticmethod
    def _serialize_observation(observation: Any) -> str:
        if isinstance(observation, BaseModel):
            return observation.model_dump_json()
        if isinstance(observation, list):
            return json.dumps(
                [
                    item.model_dump() if isinstance(item, BaseModel) else item
                    for item in observation
                ]
            )
        return json.dumps(observation)

    def next_action(self, observation: Any) -> ToolCall | None:
        if self._awaiting_tool_result:
            if self.previous_tool_call_id is None:
                raise RuntimeError(
                    "Received a tool result without a previous tool call."
                )

            self.messages.append(
                ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=self.previous_tool_call_id,
                    content=self._serialize_observation(observation),
                )
            )
            self._awaiting_tool_result = False

        response = self.model_call_executor.execute(
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools,
            )
        )

        if not response.choices:
            raise ValueError("OpenAI response did not include any choices.")

        message = response.choices[0].message
        tool_calls = message.tool_calls
        if not tool_calls:
            return None

        if len(tool_calls) > 1:
            raise ValueError(
                "OpenAIAgent supports one tool call per response; "
                f"received {len(tool_calls)}."
            )

        tool_call = tool_calls[0]
        if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
            raise TypeError("Expected a function tool call.")

        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as error:
            raise ValueError("Tool call arguments must be valid JSON.") from error

        if not isinstance(arguments, dict):
            raise ValueError("Tool call arguments must be a JSON object.")

        self.messages.append(
            ChatCompletionAssistantMessageParam(
                role="assistant",
                tool_calls=[
                    ChatCompletionMessageFunctionToolCallParam(
                        id=tool_call.id,
                        type="function",
                        function={
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    )
                ],
            )
        )

        self.previous_tool_call_id = tool_call.id
        self._awaiting_tool_result = True
        return ToolCall(
            id=tool_call.id,
            name=tool_call.function.name,
            arguments=arguments,
        )


class OpenAICommerceAgent(OpenAIAgent):
    """Backward-compatible commerce-specific prompt wrapper for OpenAIAgent."""

    def __init__(
        self,
        query: str,
        max_price: float,
        tools: list[ChatCompletionToolParam],
        model: str,
        client: OpenAI | None = None,
    ) -> None:
        self.query = query
        self.max_price = max_price
        super().__init__(
            system_prompt=(
                "You are a commerce agent. "
                "Follow the user's constraints carefully. "
                "Use the available tools to complete the request. "
                "If a tool fails, inspect the error and decide whether to "
                "try a safe alternative or stop. Do not assume a failed "
                "tool performed its action."
            ),
            user_prompt=f"Buy me {query} under {max_price} EUR.",
            tools=tools,
            model=model,
            client=client,
        )
