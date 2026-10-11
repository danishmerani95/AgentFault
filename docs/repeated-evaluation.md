# Repeated Benchmark Evaluation

LLM-backed agents can behave differently from one run to another. A single score is only one observation; repeated evaluation measures reliability across independently created agents and scenario environments.

## Run a suite repeatedly

    from agentfault.benchmarks import RepeatedBenchmarkRunner
    from agentfault.benchmarks.packs import buying_agent_v1

    result = RepeatedBenchmarkRunner(max_steps=20).run(
        buying_agent_v1(),
        my_agent_factory,
        repetitions=5,
        agent_name="my-agent:prompt-v4",
    )

    print(result.to_dict())
    print("per-case pass rates:", result.per_case_pass_rate)
    print("pass^k:", result.pass_k)
    print("mean score:", result.score_mean)
    print("score stddev:", result.score_stddev)

The runner calls the suite runner repeatedly. Each case builder should create a fresh environment and the factory should return a fresh agent for each case; the built-in packs do so.

## Metrics

- Per-case pass rate: the fraction of repetitions where that case passed.
- pass^k: the fraction of cases that passed in every repetition, a stricter reliability measure inspired by repeated-trial agent evaluation.
- Mean score: the average benchmark score across repetitions.
- Score standard deviation: the population standard deviation across valid repetition scores.
- Error count: the total number of errored cases across repetitions.

A case status of error means setup or execution failed; it is not evidence that the agent behaved safely or unsafely. If any repetition contains an error, complete is false and the aggregate mean and standard deviation are withheld rather than silently excluding invalid runs. Per-case pass rates and error counts remain available for diagnosis.

Repeated runs can be expensive when each decision invokes a hosted model. Use a small number of repetitions during development, then increase it for release evaluations. Keep the suite version, model/provider version, prompts, tool schemas, framework version, and run configuration fixed when comparing agents.

## When to use custom scenarios

The repeated runner currently operates over BenchmarkSuite. For one-off application-specific workflows, use ScenarioRunner and build your own repetition loop with a fresh environment/agent each time, or define a versioned custom BenchmarkSuite if you need consistent aggregation. See the Fault Injection guide for injecting faults at tool and model call boundaries.