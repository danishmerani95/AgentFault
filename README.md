# Agent Fault

**Break the world around your agent. Verify its behavior.**

Agent Fault is an open-source testing toolkit for tool-using AI agents. It lets you change the environment during a run—raise a price, remove inventory, suspend an account, or fail a tool—and assert that the agent still behaves safely.

It is designed for developers who need to test **their own agent with scenarios that matter to their application**, rather than rely only on a general capability score.

## How is Agent Fault different?

Agent Fault focuses on **stateful failure testing at tool-execution boundaries**. Instead of testing only a fixed prompt and the answer it produces, you can change the world *during* a run—for example, raise a price after an offer is discovered—and then check whether the agent revalidates its assumptions before taking the next action.

- **Intervene mid-run:** trigger state changes or tool failures at named tool calls.
- **Test behavior, not just text:** assert which actions were executed and whether the resulting environment state meets your rules.
- **Bring your own agent:** use custom scenarios for your application, or run an agent factory against a versioned benchmark suite.
- **Get inspectable evidence:** see the tool-call trajectory, observations, and assertion messages behind a pass or failure.

This makes Agent Fault complementary to tools focused on prompt/response grading, tracing, or production monitoring. Its distinctive job is to test how an agent responds when its tools or environment stop behaving as expected.

## Get started

Agent Fault requires **Python 3.12 or newer**. The package on PyPI is named `agentfault`.

```bash
python -m pip install agentfault
```

Start with the [Getting Started guide](docs/getting-started.md). It walks through a complete, deterministic custom scenario that runs without a model API key.

## Two ways to use it

### 1. Run a versioned benchmark

The built-in `buying-agent@1.0.0` suite has five deterministic cases covering budget and inventory changes during a purchase workflow. Supply a factory that returns a fresh Agent Fault-compatible `Agent` for each case:

```python
from agentfault.benchmarks import BenchmarkRunner
from agentfault.benchmarks.packs import buying_agent_v1

result = BenchmarkRunner(max_steps=20).run(
    buying_agent_v1(), my_agent_factory, agent_name="my-agent"
)
print(result.to_dict())
```

Here, `my_agent_factory(task, tools)` is your adapter that returns an agent implementing `Agent.next_action(observation)`; Agent Fault executes the registered tools and captures the run. See the full [benchmark guide](docs/benchmarks.md) and the [OpenAI example](examples/openai_benchmark.py) for a complete factory.

### 2. Create and run a custom scenario

Use this when you need to test a failure mode unique to your application. Wire in your own `my_agent`, isolated `world`, and `tools` (the registered tool implementations used by that world):

```python
from agentfault.testing import Scenario, ScenarioRunner
from agentfault.testing.assertions import ProhibitedActionAssertion
from agentfault.testing.perturbations import ChangePrice
from agentfault.testing.triggers import AfterTool
from agentfault.tools import ToolRegistry

scenario = Scenario(
    name="price rises during checkout",
    agent=my_agent,
    environment=world,
    perturbations=[(AfterTool("get_offers_for_product"),
                    ChangePrice("offer_sony_1", new_price=179.0))],
    assertions=[ProhibitedActionAssertion("purchase")],
)
result = ScenarioRunner(ToolRegistry(tools)).run(scenario)
assert result.passed, [a.message for a in result.assertions if not a.passed]
```

This checks that a purchase does not successfully execute after the price change. See [Custom Scenarios](docs/custom-scenarios.md) for more patterns and [Getting Started](docs/getting-started.md) for a complete runnable example that needs no model API key.

## Framework integrations

Agent Fault needs control over tool execution to record what happened and apply perturbations between decisions. The integration path depends on who owns the tool loop:

- **Your own agent / custom loop:** implement `Agent.next_action(observation)`; Agent Fault executes registered tools and returns their results.
- **OpenAI and LangChain chat models:** adapt the model's tool-call decision to the Agent contract. The LangChain example is not a transparent wrapper for every `AgentExecutor` workflow.
- **LangGraph:** use the native `LangGraphScenarioRunner` and `LangGraphToolCallInterceptor` when the graph owns execution.

See [Integrations](docs/integrations.md) for runnable examples, boundaries, and current limitations.

## Safety and project status

Use fake services, test fixtures, or an isolated sandbox—not live payment, purchase, refund, or customer systems. Agent Fault can only record and perturb tool calls that pass through its configured executor or integration hook. Read [Safety](docs/safety.md) before connecting an application.

**Project status: alpha.** APIs may change. Contributions and issue reports are welcome.

## Documentation

- [Getting Started](docs/getting-started.md) — first runnable custom scenario
- [Core Concepts](docs/concepts.md) — the mental model and execution lifecycle
- [Custom Scenarios](docs/custom-scenarios.md) — perturbations, failures, assertions, and recipes
- [Integrations](docs/integrations.md) — generic agents, OpenAI, LangChain, and LangGraph
- [Benchmarks](docs/benchmarks.md) — built-in suite, factories, and scoring
- [Results and Troubleshooting](docs/results-and-troubleshooting.md) — trajectories, errors, and debugging
- [Safety](docs/safety.md) — isolated test environments and execution boundaries
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)
