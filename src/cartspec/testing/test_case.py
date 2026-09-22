from dataclasses import dataclass, field

from cartspec.testing.assertion import Assertion
from cartspec.testing.triggers.tool import ToolTrigger


@dataclass
class TestCase:
    __test__ = False

    name: str
    assertions: list[Assertion] = field(default_factory=list)
    triggers: list[ToolTrigger] = field(default_factory=list)
