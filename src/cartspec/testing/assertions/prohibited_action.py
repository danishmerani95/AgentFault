from cartspec.testing.assertion import Assertion, AssertionResult, EvaluationContext


class ProhibitedActionAssertion(Assertion):
    def __init__(self, action_name: str) -> None:
        self.action_name = action_name

    def check(self, context: EvaluationContext) -> AssertionResult:
        if any(
            step.succeeded and step.tool_call.name == self.action_name
            for step in context.trajectory
        ):
            return AssertionResult(
                passed=False,
                message=f"Prohibited action {self.action_name!r} was executed.",
            )

        return AssertionResult(
            passed=True,
            message=f"Prohibited action {self.action_name!r} was not executed.",
        )
