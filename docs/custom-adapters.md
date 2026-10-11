# Agent integrations

The integration guidance previously in this file has moved to **[Integrations](integrations.md)** so the documentation has one canonical place to explain the generic Agent contract, OpenAI, LangChain, and LangGraph.

Recommended reading path:

1. [Getting Started](getting-started.md) — build and run a custom scenario.
2. [Custom Scenarios](custom-scenarios.md) — state changes, tool failures, and assertions.
3. [Integrations](integrations.md) — connect your own agent or framework and understand execution boundaries.

The important constraint is unchanged: Agent Fault can record and perturb only tool calls routed through its configured executor or integration hook. Use isolated test systems, never production write tools, when experimenting.
