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

        if observation is not None:
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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return None

        tool_call = message.tool_calls[0]

        if not isinstance(
            tool_call,
            ChatCompletionMessageFunctionToolCall,
        ):
            raise TypeError("Expected a function tool call.")

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

        return ToolCall(
            id=tool_call.id,
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments),
        )
