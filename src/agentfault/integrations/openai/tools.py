from agentfault.tools.tool import Tool
from openai.types.chat import ChatCompletionToolParam


def to_openai_tool(tool: Tool) -> ChatCompletionToolParam:
    schema = tool.to_openai_schema()

    return ChatCompletionToolParam(
        type="function",
        function=schema["function"],
    )


def to_openai_tools(
    tools: list[Tool],
) -> list[ChatCompletionToolParam]:
    return [to_openai_tool(tool) for tool in tools]
