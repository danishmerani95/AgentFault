from typing import Any

from agentfault.agent.base import Agent
from agentfault.commerce.tools import create_commerce_tools
from agentfault.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from agentfault.testing.perturbations import ToolFailurePerturbation
from agentfault.testing.triggers import AfterTool
from agentfault.tools import ToolCall, ToolRegistry
from examples.basic_world import create_basic_world


class RetryCreateCartAgent(Agent):
    """Small deterministic agent that retries create_cart after a tool error."""

    def __init__(self) -> None:
        self.step = 0

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.step == 0:
            self.step = 1
            return ToolCall(
                name="search_products",
                arguments={"query": "headphones"},
            )

        if self.step == 1:
            self.step = 2
            return ToolCall(name="create_cart", arguments={})

        if (
            self.step == 2
            and isinstance(observation, dict)
            and observation.get("type") == "tool_error"
            and observation.get("tool_name") == "create_cart"
        ):
            self.step = 3
            return ToolCall(name="create_cart", arguments={})

        return None


class ToolFailureRecoveryAssertion(Assertion):
    """Require one failed attempt followed by a successful retry."""

    def check(self, context: EvaluationContext) -> AssertionResult:
        create_cart_steps = [
            step for step in context.trajectory
            if step.tool_call.name == "create_cart"
        ]
        recovered = (
            any(not step.succeeded for step in create_cart_steps)
            and any(step.succeeded for step in create_cart_steps)
        )
        message = (
            "Agent recovered from the injected create_cart failure."
            if recovered
            else "Expected a failed create_cart call followed by a successful retry."
        )
        return AssertionResult(passed=recovered, message=message)


def build_scenario() -> tuple[Scenario, ToolRegistry]:
    """Fail the next create_cart call once; require the agent to recover."""
    environment = create_basic_world()
    registry = ToolRegistry(create_commerce_tools(environment))
    scenario = Scenario(
        name="recover after create_cart fails once",
        agent=RetryCreateCartAgent(),
        environment=environment,
        perturbations=[
            (
                AfterTool("search_products"),
                ToolFailurePerturbation(
                    tool_name="create_cart",
                    message="Transient create_cart failure.",
                ),
            ),
        ],
        assertions=[ToolFailureRecoveryAssertion()],
    )
    return scenario, registry
