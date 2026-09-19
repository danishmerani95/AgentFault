import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    function: Callable[..., Any]

    def execute(self, **arguments: Any) -> Any:
        return self.function(**arguments)

    def to_openai_schema(self) -> dict[str, Any]:
        signature = inspect.signature(self.function)

        properties: dict[str, Any] = {}
        required: list[str] = []

        for name, parameter in signature.parameters.items():
            if parameter.annotation is str:
                parameter_type = "string"
            elif parameter.annotation is int:
                parameter_type = "integer"
            elif parameter.annotation is float:
                parameter_type = "number"
            elif parameter.annotation is bool:
                parameter_type = "boolean"
            else:
                raise TypeError(
                    f"Unsupported parameter type for {name}: {parameter.annotation}"
                )

            properties[name] = {
                "type": parameter_type,
            }

            if parameter.default is inspect.Parameter.empty:
                required.append(name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str | None = None
