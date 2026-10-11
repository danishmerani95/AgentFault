"""Run the built-in Buying Agent benchmark against an OpenAI tool-calling agent.

Set OPENAI_API_KEY before running. All tools use AgentFault's synthetic commerce
world; this example never calls a real merchant or payment service.
"""

import json
import os

from dotenv import load_dotenv

from agentfault.agent import Agent
from agentfault.benchmarks import BenchmarkRunner
from examples.benchmark_suites import GENERAL_AGENT_SYSTEM_PROMPT, load_benchmark_suite
from agentfault.integrations.openai import OpenAIAgent, to_openai_tools
from agentfault.tools import Tool


def openai_agent_factory(task: str, tools: list[Tool]) -> Agent:
    """Build a fresh OpenAI agent for each isolated benchmark case."""
    model = os.getenv("AGENTFAULT_OPENAI_MODEL", "gpt-4o-mini")
    return OpenAIAgent(
        system_prompt=GENERAL_AGENT_SYSTEM_PROMPT,
        user_prompt=task,
        tools=to_openai_tools(tools),
        model=model,
    )


def main() -> int:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "Set OPENAI_API_KEY to run this example. "
            "All tool execution still stays in a synthetic local test world."
        )

    suite_id = os.getenv("AGENTFAULT_BENCHMARK_SUITE", "buying-agent")
    suite = load_benchmark_suite(suite_id)
    result = BenchmarkRunner(max_steps=20).run(
        suite,
        openai_agent_factory,
        agent_name=f"openai:{os.getenv('AGENTFAULT_OPENAI_MODEL', 'gpt-4o-mini')}",
    )
    print(json.dumps(result.to_dict(), indent=2))
    # An execution error makes the run invalid. Behavioral failures are reported
    # in the score and case results instead of being hidden by an exception.
    return 0 if result.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
