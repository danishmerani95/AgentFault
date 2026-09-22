from dataclasses import dataclass

from cartspec.testing.mutations import Mutation


@dataclass
class ToolTrigger:
    tool_name: str
    mutation: Mutation
