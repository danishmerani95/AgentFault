from typing import Any

from agentfault.testing.assertions import NoActionAttemptedAssertion
from agentfault.testing.assertion import EvaluationContext
from agentfault.tools import ToolCall
from agentfault.trajectory import TrajectoryStep


def test_fails_when_action_was_attempted_even_if_execution_failed() -> None:
    context = EvaluationContext(
        final_observation=None,
        trajectory=[
            TrajectoryStep(
                tool_call=ToolCall("delete_record", {}),
                observation={"type": "tool_error"},
                error={"type": "TimeoutError", "message": "timed out"},
            )
        ],
        error=None,
        environment={},
    )

    result = NoActionAttemptedAssertion("delete_record").check(context)

    assert result.passed is False
    assert "attempted" in result.message


def test_passes_when_prohibited_action_is_absent() -> None:
    context = EvaluationContext(
        final_observation=None,
        trajectory=[
            TrajectoryStep(
                tool_call=ToolCall("read_record", {}),
                observation={"id": "test"},
            )
        ],
        error=None,
        environment={},
    )

    result = NoActionAttemptedAssertion("delete_record").check(context)

    assert result.passed is True
    assert "not attempted" in result.message
