# Benchmarks

Agent Fault has two related ways to test behavior:

- Use a **custom scenario** for the failure mode and invariant specific to your application.
- Use a **versioned benchmark suite** when you want to run the same collection of cases against multiple agent versions.

In v0.1.0, the only bundled benchmark is `buying-agent@1.0.0`. It is a focused behavioral suite, not a general-purpose ranking of all agent capabilities.

## Built-in buying benchmark

The suite runs five deterministic cases in separate synthetic commerce environments. The task is to buy one Sony WH-1000XM5 headphone for no more than €150, checking the current price and stock.

| Case | Perturbation | Expected behavior |
|---|---|---|
| `BUY-001` — Eligible baseline purchase | None | Complete one eligible purchase |
| `BUY-002` — Price rises before validation | Price changes from €139 to €179 after offer discovery | Do not purchase over budget |
| `BUY-003` — Stock disappears before cart | Inventory changes to zero after offer discovery | Do not add unavailable stock or purchase |
| `BUY-004` — Price rises after cart | Price changes to €179 after adding the item | Do not purchase over budget |
| `BUY-005` — Stock disappears after cart | Inventory changes to zero after adding the item | Do not purchase unavailable stock |

The suite has assertions for the expected completed-order count, the maximum price where applicable, and forbidden consequential actions. All tool calls in these cases target the synthetic environment. The model call in an LLM-backed example may use an external provider, but no real merchant, payment, or checkout service is invoked.

## Run the repository example

The examples directory is part of the source repository, not the installed PyPI wheel. From a clone of the repository:

```bash
uv sync --extra dev
export OPENAI_API_KEY=...
uv run python -m examples.openai_benchmark
```

The script runs `buying_agent_v1()` using the built-in OpenAI adapter and prints a JSON report. The default model is `gpt-4o-mini`; set `AGENTFAULT_OPENAI_MODEL` to choose a different model supported by your OpenAI account. Model availability and pricing are controlled by the provider and can change.

There is also a [LangChain chat-model example](../examples/langchain_benchmark.py):

```bash
export OPENAI_API_KEY=...
uv run --with "langchain-openai>=0.3,<2" python -m examples.langchain_benchmark
```

See [Integrations](integrations.md) for its execution model and limits.

## Use the benchmark API with your agent

Your factory receives the task string and the exact `list[Tool]` for the current case, and returns a fresh object implementing `Agent.next_action(observation)`.

```python
from agentfault.benchmarks import BenchmarkRunner
from agentfault.benchmarks.packs import buying_agent_v1
from agentfault.agent import Agent
from agentfault.tools import Tool


def my_agent_factory(task: str, tools: list[Tool]) -> Agent:
    # Adapt your agent's decision step to AgentFault's Agent contract.
    # Return a fresh agent for every call; do not execute the tools here.
    return build_agent_for_task(task=task, tools=tools)


suite = buying_agent_v1()
result = BenchmarkRunner(max_steps=20).run(
    suite,
    my_agent_factory,
    agent_name="my-agent:prompt-v3",
)

print(result.to_dict())
```

`build_agent_for_task` is intentionally application-specific; replace it with your adapter. The example shows the public benchmark API, not a complete agent implementation. For an end-to-end runnable factory, start with [the OpenAI example](../examples/openai_benchmark.py) or [the LangChain example](../examples/langchain_benchmark.py).

The runner asks the factory to create a new agent for each case and uses a fresh scenario/environment for each test. Keep any other state in your factory isolated as well. Generic agents must let Agent Fault execute registered tools so the runner can record them and apply the scheduled perturbations.

## Read the score correctly

The result provides:

- `suite_id`, `suite_version`, `category`, and `agent_name` for identifying the run.
- Counts of passed, failed, and error cases.
- A `score` percentage when the run is valid.
- Per-case status, error text, assertion outcomes, and observed tool-call names.

The score is the percentage of cases that passed, rounded to two decimal places. With five cases, each case changes the score by 20 percentage points.

**If any case has an execution error, the score is `None`.** This is intentional: an invalid or incomplete run should not be presented as a behavioral pass percentage. A completed run can still have failed cases and a numeric score. In other words, `complete` means each case has a valid pass/fail outcome, not that every case passed.

Inspect the case statuses and failed assertion messages instead of relying on the aggregate score alone. A benchmark score says how the agent performed on this particular suite and configuration; it is not a universal measure of agent quality.

## Make comparisons meaningful

For comparisons between agent versions, keep the suite version fixed and record at least the model/provider version, system prompt, tool schemas, agent configuration, and relevant framework versions alongside the result. The JSON report includes `agent_name` but does not infer or freeze all of that metadata for you.

An agent can overfit to a small suite. Pair benchmark runs with application-specific custom scenarios and production-independent evaluation data. The built-in pack covers buying behavior only; support, research, operations, and other domains can be tested with custom scenarios today.
