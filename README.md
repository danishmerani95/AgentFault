# AgentFault

**Break the world around your agent. Verify its behavior.**

AgentFault tests tool-using AI agents against changing conditions: a price rises, inventory disappears, an account is suspended, or a tool fails while the agent is working.

It offers two APIs over the same stateful testing engine.

## 1. Benchmark API

**Use it to compare an agent against a reusable, versioned test suite.**

The built-in `buying-agent@1.0.0` benchmark contains five deterministic scenarios covering:

- Buying an eligible offer within budget.
- Price increases before validation.
- Inventory disappearing before cart creation.
- Price increases after an item enters the cart.
- Inventory disappearing after an item enters the cart.

A benchmark returns a pass percentage, per-case results, failed assertions, and observed tool calls. If any case has an execution error, the headline score is withheld rather than treating an invalid run as a pass or failure.

The API accepts an agent factory that implements AgentFault's `Agent` contract. OpenAI has a built-in adapter; other frameworks can provide an adapter for their tool-call loop.

Run the OpenAI example (requires an OpenAI API key; all tools still use a synthetic test environment):

```bash
uv sync --extra dev
export OPENAI_API_KEY=...
uv run python -m examples.openai_benchmark
```

The example is in [`examples/openai_benchmark.py`](examples/openai_benchmark.py). It prints a JSON report and can be adapted to use your own prompts, model, and agent.

## 2. Custom Scenario API

**Use it to test a failure mode specific to your application.**

A scenario defines your agent, isolated environment and tools, an optional perturbation, and assertions about acceptable behavior. Use it for buying, support, research, operations, or any workflow where an agent's actions depend on tool results or changing state.

For an agent that implements `Agent`, compose a `Scenario` and run it with `ScenarioRunner`:

```python
from agentfault.testing import Scenario, ScenarioRunner
from agentfault.testing.assertions import MaxPriceAssertion
from agentfault.testing.perturbations import ChangePrice
from agentfault.testing.triggers import AfterTool

scenario = Scenario(
    name="price changes during checkout",
    agent=agent_under_test,
    environment=test_environment,
    perturbations=[
        (AfterTool("get_offers_for_product"),
         ChangePrice("offer_sony_1", new_price=179.0)),
    ],
    assertions=[MaxPriceAssertion(max_price=150.0)],
)
result = ScenarioRunner(tool_registry).run(scenario)
assert result.passed, [item.message for item in result.assertions if not item.passed]
```

For a graph that owns its own decision loop, use its integration runner instead of wrapping the entire graph as a generic `Agent`.

Run the LangGraph example (requires LangGraph; no model API key is needed):

```bash
uv run --with "langgraph>=1.0,<2" python -m examples.langgraph_integration
```

The [LangGraph example](examples/langgraph_integration.py) uses a real `StateGraph` and `ToolNode`, a scripted decision node, and a fake account/refund world. It shows a custom scenario that suspends an account after lookup and checks that no refund tool is called. The current LangGraph integration supports synchronous `invoke`, sequential calls routed through the configured `ToolNode`; async execution, parallel calls, and other tool paths are not yet supported.

## Use cases

- **Buying agents:** stop unsafe purchases when prices or inventory change.
- **Support agents:** verify permissions and account state before refunds or account changes.
- **Search and research agents:** test stale, missing, or contradictory information.
- **Operations and workflow agents:** inject tool failures and check recovery or safe stopping.

The built-in benchmark currently covers buying. Other roles can be tested today with custom scenarios; additional benchmark packs can use the same versioned suite API.

## Safety and scope

Use fixtures, fake services, or an isolated sandbox. AgentFault does not make production tools safe automatically. Only actions routed through the configured executor/interceptor are recorded and can be perturbed.

Project status: **alpha**. APIs may change. See [custom adapter notes](docs/custom-adapters.md), [contributing](CONTRIBUTING.md), and the [changelog](CHANGELOG.md).
