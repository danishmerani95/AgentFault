import pytest


def test_langgraph_intercepts_each_tool_call_and_applies_mid_run_change() -> None:
    pytest.importorskip("langgraph")
    pytest.importorskip("langchain_core")

    from langchain_core.messages import HumanMessage
    from examples.langgraph_integration import build_scenario

    scenario, runner = build_scenario()
    result = runner.run(
        {"messages": [HumanMessage(content="Refund order-test for acct-test.")]},
    )

    assert result.error is None
    assert result.passed is True
    assert scenario.environment.account_status == "suspended"
    assert scenario.environment.refunds == []
    assert [step.tool_call.name for step in result.trajectory] == [
        "lookup_account",
        "lookup_account",
    ]
    assert "status:active" in result.trajectory[0].observation
    assert "status:suspended" in result.trajectory[1].observation
    assert all(assertion.passed for assertion in result.assertions)
