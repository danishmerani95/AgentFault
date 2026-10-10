import json
import os
from typing import Any

from pydantic import BaseModel

from cartspec.agent import Agent
from cartspec.tools.tool import ToolCall
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


class OpenAICommerceAgent(Agent):
    def __init__(
        self,
        query: str,
        max_price: float,
        tools: list[ChatCompletionToolParam],
        model: str,
    ) -> None:
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        self.model = model
        self.query = query
        self.max_price = max_price
        self.tools = tools

        self.messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": (
                    "You are a commerce agent. "
                    "Follow the user's constraints carefully. "
                    "Use the available tools to complete the request."
                ),
            },
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Buy me {query} under {max_price} EUR.",
            ),
        ]

        self.previous_tool_call_id: str | None = None
        self._awaiting_tool_result = False

    def next_action(self, observation: Any) -> ToolCall | None:
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

        if self._awaiting_tool_result:
            if self.previous_tool_call_id is None:
                raise RuntimeError(
                    "Received a tool result without a previous tool call."
                )

            self.messages.append(
                ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=self.previous_tool_call_id,
                    content=_serialize_observation(observation),
                )
            )
            self._awaiting_tool_result = False

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
        )

        if not response.choices:
            raise ValueError("OpenAI response did not include any choices.")

        message = response.choices[0].message

        tool_calls = message.tool_calls
        if not tool_calls:
            return None

        if len(tool_calls) > 1:
            raise ValueError(
                "OpenAICommerceAgent supports one tool call per response; "
                f"received {len(tool_calls)}."
            )

        tool_call = tool_calls[0]

        if not isinstance(
            tool_call,
            ChatCompletionMessageFunctionToolCall,
        ):
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
