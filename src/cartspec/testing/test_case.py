from dataclasses import dataclass

from cartspec.testing.assertion import Assertion


@dataclass
class TestCase:
    __test__ = False

    name: str
    assertions: list[Assertion]
