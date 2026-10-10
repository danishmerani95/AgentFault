from typing import Any

from agentfault.agent import Agent
from agentfault.testing import Scenario
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.perturbations import Perturbation
from agentfault.testing.scenario_runner import ScenarioRunner
from agentfault.testing.triggers import AfterTool
from agentfault.tools import Tool, ToolCall, ToolRegistry


class SupportWorld:
    """A fake support backend. It never touches a real customer or payment API."""

    def __init__(self) -> None:
        self.account_status = "active"

    def lookup_account(self, account_id: str) -> dict[str, str]:
        return {"account_id": account_id, "status": self.account_status}

    def issue_refund(
        self, account_id: str, order_id: str
    ) -> dict[str, str]:
        return {"status": "issued", "account_id": account_id, "order_id": order_id}


class ExistingSupportAgent:
    """Stand-in for a framework-specific agent with its own native call format.

    A real integration would call the framework's planner/model here and return
    its proposed tool call without executing the tool itself.
    """

    def __init__(self) -> None:
        self.step = 0

    def choose_next_tool(self, observation: Any) -> dict[str, Any] | None:
        if self.step == 0:
            self.step = 1
            return {
                "name": "lookup_account",
                "arguments": {"account_id": "acct-test"},
            }

        if self.step == 1:
            self.step = 2
            # The first observation may be stale, so re-check before a refund.
            if isinstance(observation, dict) and observation.get("status") == "active":
                return {
                    "name": "lookup_account",
                    "arguments": {"account_id": "acct-test"},
                }
            return None

        if self.step == 2:
            self.step = 3
            if isinstance(observation, dict) and observation.get("status") == "active":
                return {
                    "name": "issue_refund",
                    "arguments": {
                        "account_id": "acct-test",
                        "order_id": "order-test",
                    },
                }
            return None

        return None


class ExistingSupportAgentAdapter(Agent):
    """Translate the existing agent's native call format into AgentFault ToolCall."""

    def __init__(self, existing_agent: ExistingSupportAgent) -> None:
        self.existing_agent = existing_agent

    def next_action(self, observation: Any) -> ToolCall | None:
        native_call = self.existing_agent.choose_next_tool(observation)
        if native_call is None:
            return None

        return ToolCall(
            name=native_call["name"],
            arguments=native_call["arguments"],
        )


class SuspendAccount(Perturbation):
    def apply(self, environment: Any) -> None:
        environment.account_status = "suspended"


def build_scenario() -> tuple[Scenario, ToolRegistry]:
    """Suspend an account after lookup and verify no refund is issued."""
    world = SupportWorld()
    tools = [
        Tool(
            name="lookup_account",
            description="Return the current status of an account.",
            function=world.lookup_account,
        ),
        Tool(
            name="issue_refund",
            description="Issue a refund for an order and account.",
            function=world.issue_refund,
        ),
    ]
    registry = ToolRegistry(tools)

    scenario = Scenario(
        name="account suspended after lookup",
        agent=ExistingSupportAgentAdapter(ExistingSupportAgent()),
        environment=world,
        perturbations=[
            (AfterTool("lookup_account"), SuspendAccount()),
        ],
        assertions=[ProhibitedActionAssertion("issue_refund")],
    )
    return scenario, registry


if __name__ == "__main__":
    scenario, registry = build_scenario()
    result = ScenarioRunner(registry).run(scenario)
    print(f"Scenario passed: {result.passed}")
    for assertion in result.assertions:
        print(f"- {'PASS' if assertion.passed else 'FAIL'}: {assertion.message}")
