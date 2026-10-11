from typing import Any

from agentfault.testing.assertion import Assertion, AssertionResult, EvaluationContext


class CollectionLengthAssertion(Assertion):
    """Assert the length of a named list-like environment field."""

    def __init__(self, attribute: str, expected_length: int) -> None:
        if expected_length < 0:
            raise ValueError("expected_length must not be negative.")
        self.attribute = attribute
        self.expected_length = expected_length

    def check(self, context: EvaluationContext) -> AssertionResult:
        collection = getattr(context.environment, self.attribute, None)
        actual = len(collection) if collection is not None else None
        passed = actual == self.expected_length
        return AssertionResult(
            passed=passed,
            message=(
                f"Expected {self.attribute} length {self.expected_length}; "
                f"found {actual}."
            ),
        )


class AttributeEqualsAssertion(Assertion):
    """Assert that one environment field equals its expected value."""

    def __init__(self, attribute: str, expected: Any) -> None:
        self.attribute = attribute
        self.expected = expected

    def check(self, context: EvaluationContext) -> AssertionResult:
        actual = getattr(context.environment, self.attribute, None)
        passed = actual == self.expected
        return AssertionResult(
            passed=passed,
            message=f"Expected {self.attribute}={self.expected!r}; found {actual!r}.",
        )
