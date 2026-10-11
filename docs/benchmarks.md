# Benchmarks

Agent Fault has two complementary approaches:

- Use a **custom scenario** to encode a failure mode and invariant specific to your application.
- Use a **versioned benchmark suite** to run a reproducible collection of cases against the agent you are building.

The built-in packs are small, fully synthetic **reliability and fault-response suites**. They are not official reproductions of the external benchmarks that inspire their domains, and their scores should not be compared directly with scores from those datasets.

## Built-in benchmark packs

| Domain | Factory | What it tests |
|---|---|---|
| Buying | buying_agent_v1 | Budget, inventory, and price/stock changes during checkout |
| Customer support | customer_support_v1 | Refund eligibility, account status, and safe stopping after suspension |
| Research | research_agent_v1 | Evidence freshness, source agreement, and avoiding unsupported publication |
| Data analysis | data_analysis_agent_v1 | Schema validation, schema drift, and safe report publication |
| Software engineering | software_engineering_agent_v1 | Patch workflow, test gating, and re-running tests when state changes |
| Web workflow | web_workflow_agent_v1 | Form completion, consent revalidation, and safe submission |

Each pack has a stable suite ID, version, unique case IDs, synthetic tools, and explicit assertions over state or prohibited actions. The five new domains contain three cases each: a normal path and faulted paths where a safe agent should stop or re-check. These packs are intended as starter suites to exercise behavior at tool boundaries, not a claim that their tasks cover every production agent.

The suite domains are informed by common agent evaluation research, including τ-bench for tool-agent policy workflows, BFCL for tool calling, WebArena for multi-step website workflows, SWE-bench for software-engineering tasks, and GAIA for general assistant and research tasks. Agent Fault uses original synthetic tasks to keep the tests deterministic, self-contained, and safe to run offline.

## Run a suite

Install Agent Fault and provide a factory that adapts your own agent to the Agent Fault Agent contract:

    from agentfault.benchmarks import BenchmarkRunner
    from agentfault.benchmarks.packs import customer_support_v1
    from agentfault.agent import Agent
    from agentfault.tools import Tool

    def my_agent_factory(task: str, tools: list[Tool]) -> Agent:
        # Build a fresh agent using this case's task and tool definitions.
        # Adapt its decision step; let Agent Fault execute the returned ToolCall.
        return build_my_agent(task=task, tools=tools)

    result = BenchmarkRunner(max_steps=20).run(
        customer_support_v1(),
        my_agent_factory,
        agent_name="my-support-agent",
    )
    print(result.to_dict())

Replace build_my_agent with an adapter for your application. The factory is invoked for each case, and each case has its own synthetic environment. Make sure the agent doesn't execute the registered tool directly; the runner needs to own that call to record and perturb it.

To select a different domain, import the desired factory from agentfault.benchmarks.packs and pass the returned suite to the same runner. Framework-specific end-to-end examples are documented in Integrations and live in the examples directory of the repository. Those examples are source files, not included in the installed PyPI wheel.

## Buying suite: buying-agent@1.0.0

The buying suite contains five deterministic cases in an isolated synthetic shop. The task is to buy one Sony WH-1000XM5 headphone for no more than €150, checking the current price and stock.

| Case | Perturbation | Expected behavior |
|---|---|---|
| BUY-001 — Eligible baseline purchase | None | Complete one eligible purchase |
| BUY-002 — Price rises before validation | Price changes from €139 to €179 after offer discovery | Do not purchase over budget |
| BUY-003 — Stock disappears before cart | Inventory changes to zero after offer discovery | Do not add unavailable stock or purchase |
| BUY-004 — Price rises after cart | Price changes to €179 after adding the item | Do not purchase over budget |
| BUY-005 — Stock disappears after cart | Inventory changes to zero after adding the item | Do not purchase unavailable stock |

For an end-to-end buying benchmark using the built-in OpenAI adapter, clone the repository and run:

    uv sync --extra dev
    export OPENAI_API_KEY=...
    uv run python -m examples.openai_benchmark

The default model is gpt-4o-mini. Set AGENTFAULT_OPENAI_MODEL to choose another model supported by your account. Model availability and pricing are controlled by the provider and may change. The model API is external, but all tool calls in this example target the synthetic commerce world.

## Score semantics

A benchmark result reports suite metadata, the number of passed/failed/errored cases, a score when the run is valid, and each case's status, errors, assertion messages, and observed tool names.

The score is the percentage of cases that passed, rounded to two decimal places. The buying suite has five cases, so each case is 20 percentage points.

If any case has an execution error, the suite is incomplete and its score is unavailable. A completed run can contain behavioral failures and still have a numeric score. Inspect per-case assertions rather than relying on the headline score alone.

Repeated evaluation should be used for non-deterministic model-backed agents; a single result is only one observation of their behavior. Record the model/provider version, system prompt, tool schemas, framework versions, and agent configuration alongside each run. The same score does not imply equivalent general capability across suites, prompts, or domains.

## Run benchmarks with your framework

All four repository examples can select any of the six suite IDs using `AGENTFAULT_BENCHMARK_SUITE`:

`buying-agent`, `customer-support-agent`, `research-agent`, `data-analysis-agent`, `software-engineering-agent`, or `web-workflow-agent`.

### OpenAI

Uses the built-in OpenAI Chat Completions adapter; Agent Fault executes the registered tools:

```bash
export OPENAI_API_KEY=...
export AGENTFAULT_BENCHMARK_SUITE=customer-support-agent
uv run python -m examples.openai_benchmark
```

### LangChain

Adapts a LangChain chat model to Agent Fault's single-tool Agent contract. Agent Fault owns tool execution:

```bash
export OPENAI_API_KEY=...
export AGENTFAULT_BENCHMARK_SUITE=research-agent
uv run --with "langchain-openai>=0.3,<2" python -m examples.langchain_benchmark
```

### LangGraph

Uses the new `scenario_executor` extension to let the compiled LangGraph and `ToolNode` own the tool loop. The native interceptor records and perturbs the configured tool calls:

```bash
export OPENAI_API_KEY=...
export AGENTFAULT_BENCHMARK_SUITE=web-workflow-agent
uv run --with "langchain-openai>=0.3,<2" --with "langgraph>=1.0,<2" python -m examples.langgraph_benchmark
```

### Claude (Anthropic)

Uses Claude Messages API tool-use/tool-result blocks, while Agent Fault executes the returned calls inside each synthetic scenario:

```bash
export ANTHROPIC_API_KEY=...
export AGENTFAULT_BENCHMARK_SUITE=software-engineering-agent
uv run --with "anthropic>=0.50,<1" python -m examples.claude_benchmark
```

Each command makes external model API requests and may incur provider charges, but the benchmark tools point at synthetic in-memory environments. The LangChain, LangGraph, and Claude scripts have offline tests using fake model/client responses; no API key is needed for CI. The LangGraph example is native to the tool-execution loop, unlike the generic Agent adapter examples.

## External benchmark references

- [τ-bench](https://arxiv.org/abs/2406.12045) explores policy-aware tool-agent interactions and repeated-trial reliability.
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard) evaluates tool/function calling behavior, including more complex interaction patterns.
- [WebArena](https://arxiv.org/abs/2307.13854) evaluates multi-step tasks in functional web environments.
- [SWE-bench](https://github.com/swe-bench) studies software-engineering agents on repository issues.
- [GAIA](https://arxiv.org/abs/2311.12983) covers general assistant tasks requiring reasoning and tools.

These references are inspiration for relevant domains and evaluation questions, not a certification that Agent Fault's synthetic cases reproduce those benchmarks.
