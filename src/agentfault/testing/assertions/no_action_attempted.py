from agentfault.testing.assertion import Assertion, AssertionResult, EvaluationContext


class NoActionAttemptedAssertion(Assertion):
    """Require that a named action does not appear anywhere in the trajectory.

    Unlike ProhibitedActionAssertion, this assertion fails even when the tool
    call was attempted but its execution failed or timed out.
    """

    def __init__(self, action_name: str) -> None:
        if not action_name.strip():
            raise ValueError("action_name must not be empty.")
        self.action_name = action_name

    def check(self, context: EvaluationContext) -> AssertionResult:
        attempted = any(
            step.tool_call.name == self.action_name for step in context.trajectory
        )
        return AssertionResult(
            passed=not attempted,
            message=(
                f"Tool {self.action_name!r} was not attempted."
                if not attempted
                else f"Prohibited tool {self.action_name!r} was attempted."
            ),
        )
