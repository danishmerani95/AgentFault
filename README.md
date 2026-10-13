# Agent Fault

**Break the world around your agent. Verify its behavior.**

Agent Fault is an open-source testing toolkit for tool-using AI agents. It lets you change the environment during a run—raise a price, remove inventory, suspend an account, or fail a tool—and assert that the agent still behaves safely.

It is designed for developers who need to test **their own agent with scenarios that matter to their application**, rather than rely only on a general capability score.

## Get started

Agent Fault requires **Python 3.12 or newer**. The package on PyPI is named `agentfault`.

```bash
python -m pip install agentfault
```

Start with the [Getting Started guide](docs/getting-started.md). It walks through a complete, deterministic custom scenario that runs without a model API key. Then read [Core Concepts](docs/concepts.md) to understand the agent, tools, environment, perturbations, assertions, and results.

## What you can test

- **Changing state:** a price or inventory count changes after a tool call.
- **Tool failures:** a dependency fails and the agent must recover or stop safely.
- **Prohibited actions:** a refund, purchase, or other consequential tool must not be called in a risky state.
- **Application-specific rules:** define custom assertions over the recorded trajectory and test environment.

Agent Fault has two complementary APIs:

### Custom scenarios

Build focused tests around your own failure modes. A scenario combines an agent, an isolated environment, a tool registry, optional perturbations and triggers, and assertions.

Start here if you are integrating your own agent: [Getting Started](docs/getting-started.md) → [Custom Scenarios](docs/custom-scenarios.md) → [Integrations](docs/integrations.md).

### Versioned benchmarks

Use a reusable suite to compare agent behavior across a fixed set of cases. The first built-in suite, `buying-agent@1.0.0`, contains five deterministic tests for budget and inventory constraints under mid-run changes.

The benchmark API accepts an agent factory implementing Agent Fault's `Agent` contract. OpenAI and LangChain chat-model examples are available in the repository and require an API key:

```bash
uv sync --extra dev
export OPENAI_API_KEY=...
uv run python -m examples.openai_benchmark
```

See [Benchmarks](docs/benchmarks.md) for score semantics and the full list of cases. Repository examples are not included in the installed PyPI wheel; clone the repository before running commands under `examples/`.

## Framework integrations

Agent Fault needs control over tool execution to record what happened and apply perturbations between decisions. The integration path depends on who owns the tool loop:

- **Your own agent / custom loop:** implement `Agent.next_action(observation)`; Agent Fault executes registered tools and returns their results.
- **LangChain chat models:** the example adapts a model's single tool-call decision to the Agent contract. It is not a transparent wrapper for every `AgentExecutor` workflow.
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
- [API Stability](docs/api-stability.md) — compatibility and semantic-versioning policy for the first stable release
- [Release Checklist](docs/releasing.md) — stable-release gates and publishing steps
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)
