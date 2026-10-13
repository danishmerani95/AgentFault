"""A deterministic LangGraph example using AgentFault's ToolNode interceptor.

No model API key is needed. The "agent" node is scripted to make the tool-call
sequence deterministic, so the example isolates the integration semantics.
Install LangGraph separately with: pip install "langgraph>=1.0,<2".
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from agentfault.integrations.langgraph import (
    LangGraphScenarioRunner,
    LangGraphToolCallInterceptor,
)
from agentfault.testing import Scenario
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.perturbations import Perturbation
from agentfault.testing.triggers import AfterTool


class SupportWorld:
    """Tiny fake backend; no real account or payment services are called."""

    def __init__(self) -> None:
        self.account_status = "active"
        self.refunds: list[tuple[str, str]] = []

    def lookup_account(self, account_id: str) -> str:
        return f"account:{account_id};status:{self.account_status}"

    def issue_refund(self, account_id: str, order_id: str) -> str:
        self.refunds.append((account_id, order_id))
        return "refund issued"


class SuspendAccount(Perturbation):
    def apply(self, environment: Any) -> None:
        environment.account_status = "suspended"


def build_scenario() -> tuple[Scenario, LangGraphScenarioRunner]:
    world = SupportWorld()

    @tool
    def lookup_account(account_id: str) -> str:
        """Return the current support account status."""
        return world.lookup_account(account_id)

    @tool
    def issue_refund(account_id: str, order_id: str) -> str:
        """Issue a refund (only used in this fake test world)."""
        return world.issue_refund(account_id, order_id)

    interceptor = LangGraphToolCallInterceptor(
        environment=world,
        perturbations=[
            (AfterTool("lookup_account"), SuspendAccount()),
        ],
    )

    tool_node = ToolNode(
        [lookup_account, issue_refund],
        wrap_tool_call=interceptor,
        awrap_tool_call=interceptor.awrap_tool_call,
    )

    def scripted_agent(state: MessagesState) -> dict[str, list[AIMessage]]:
        """Stand in for a model while preserving LangGraph's real execution loop."""
        last_message = state["messages"][-1]

        if isinstance(last_message, HumanMessage):
            tool_call = {
                "name": "lookup_account",
                "args": {"account_id": "acct-test"},
                "id": "lookup-1",
                "type": "tool_call",
            }
            return {"messages": [AIMessage(content="", tool_calls=[tool_call])]}

        if isinstance(last_message, ToolMessage):
            if "status:active" in str(last_message.content):
                # This result may be stale, so re-check before consequential actions.
                tool_call = {
                    "name": "lookup_account",
                    "args": {"account_id": "acct-test"},
                    "id": "lookup-2",
                    "type": "tool_call",
                }
                return {"messages": [AIMessage(content="", tool_calls=[tool_call])]}

            if "status:suspended" in str(last_message.content):
                return {
                    "messages": [
                        AIMessage(
                            content=(
                                "The account is suspended; I will not issue a refund."
                            )
                        )
                    ]
                }

        return {"messages": [AIMessage(content="No action taken.")]}

    def route_after_agent(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    builder = StateGraph(MessagesState)
    builder.add_node("agent", scripted_agent)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")
    graph = builder.compile()

    scenario = Scenario(
        name="account suspended after the first lookup",
        agent=graph,
        environment=world,
        perturbations=interceptor.perturbations,
        assertions=[ProhibitedActionAssertion("issue_refund")],
    )
    return scenario, LangGraphScenarioRunner(scenario, interceptor)


if __name__ == "__main__":
    scenario, runner = build_scenario()
    result = runner.run(
        {"messages": [HumanMessage(content="Refund order-test for acct-test.")]},
    )
    print(f"Scenario passed: {result.passed}")
    for assertion in result.assertions:
        print(f"- {'PASS' if assertion.passed else 'FAIL'}: {assertion.message}")
    print(f"Tool calls: {[step.tool_call.name for step in result.trajectory]}")
