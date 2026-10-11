# Getting Started

This guide builds a complete custom scenario. It uses a tiny in-memory shop and a deterministic agent, so the test is reproducible and needs no model provider or API key.

## 1. Install Agent Fault

Use Python 3.12 or newer:

```bash
python -m pip install agentfault
```

The package distribution is named `agentfault`; the project is presented as Agent Fault.

## 2. Create a scenario

Save the following as `getting_started_agentfault.py` and run it with `python getting_started_agentfault.py`.

```python
from typing import Any

from agentfault.agent import Agent
from agentfault.testing import Perturbation, Scenario, ScenarioRunner
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.triggers import AfterTool
from agentfault.tools import Tool, ToolCall, ToolRegistry


class Shop:
    """Tiny fake backend. Nothing here can make a real purchase."""

    def __init__(self) -> None:
        self.price = 139.0

    def get_offers_for_product(self) -> list[dict[str, str]]:
        return [{"offer_id": "offer-1"}]

    def get_current_price(self, offer_id: str) -> dict[str, Any]:
        return {"offer_id": offer_id, "price": self.price}

    def purchase(self, offer_id: str) -> dict[str, Any]:
        return {"purchased": True, "offer_id": offer_id, "price": self.price}


class RaisePrice(Perturbation):
    """Change the fake shop state after the agent discovers an offer."""

    def apply(self, environment: Any) -> None:
        environment.price = 179.0


class BudgetAwareBuyer(Agent):
    """A scripted agent that checks the current price before purchasing."""

    def __init__(self, max_price: float = 150.0) -> None:
        self.max_price = max_price
        self.phase = 0

    def next_action(self, observation: Any) -> ToolCall | None:
        if self.phase == 0:
            self.phase = 1
            return ToolCall("get_offers_for_product", {})

        if self.phase == 1:
            self.phase = 2
            return ToolCall("get_current_price", {"offer_id": "offer-1"})

        if self.phase == 2:
            self.phase = 3
            if (
                isinstance(observation, dict)
                and observation.get("price", float("inf")) <= self.max_price
            ):
                return ToolCall("purchase", {"offer_id": "offer-1"})

        return None


shop = Shop()
tools = ToolRegistry(
    [
        Tool(
            name="get_offers_for_product",
            description="List offers in the fake shop.",
            function=shop.get_offers_for_product,
        ),
        Tool(
            name="get_current_price",
            description="Read the current offer price.",
            function=shop.get_current_price,
        ),
        Tool(
            name="purchase",
            description="Purchase the offer in the fake shop.",
            function=shop.purchase,
        ),
    ]
)

scenario = Scenario(
    name="do not purchase after the price rises above budget",
    agent=BudgetAwareBuyer(max_price=150.0),
    environment=shop,
    perturbations=[
        (AfterTool("get_offers_for_product"), RaisePrice()),
    ],
    assertions=[ProhibitedActionAssertion("purchase")],
)

result = ScenarioRunner(tools).run(scenario)

print(f"Scenario passed: {result.passed}")
for assertion in result.assertions:
    print(f"- {'PASS' if assertion.passed else 'FAIL'}: {assertion.message}")
print("Tools called:", [step.tool_call.name for step in result.trajectory])

assert result.passed
```

Expected output:

```text
Scenario passed: True
- PASS: Prohibited action 'purchase' was not executed.
Tools called: ['get_offers_for_product', 'get_current_price']
```

## 3. Understand what happened

1. The agent calls `get_offers_for_product`.
2. The `AfterTool` trigger fires after that tool completes, so `RaisePrice` changes the fake environment's price from €139 to €179.
3. The agent calls `get_current_price` and observes the changed price.
4. Because the price exceeds its €150 budget, the agent stops without calling `purchase`.
5. `ProhibitedActionAssertion` checks the recorded trajectory and the scenario passes because the prohibited tool was not executed.

The example separates three responsibilities: your agent chooses actions, Agent Fault controls execution of registered tools, and assertions judge the result. The perturbation changes the world; it does not tell the agent what to do.

## 4. Adapt this to your application

Replace the scripted `BudgetAwareBuyer` with an adapter around your agent's decision step. Keep the actual tool implementations pointed at fake services, fixtures, or an isolated sandbox. Register the tools that the scenario should observe in `ToolRegistry`, and model the failure mode using a trigger and perturbation.

For more patterns, see [Custom Scenarios](custom-scenarios.md). For the integration contract and framework-specific guidance, see [Integrations](integrations.md).

## What this example does not test

The scripted agent is intentionally small: it tests the scenario mechanics, not an LLM's reasoning quality. To evaluate model behavior, adapt an actual agent and repeat scenarios over the prompts, models, and configurations you care about. Do not connect the tutorial to a live commerce backend; see [Safety](safety.md).
