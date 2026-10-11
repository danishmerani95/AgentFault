"""Synthetic research benchmark focused on current and consistent evidence."""

from agentfault.benchmarks import AgentFactory, BenchmarkCase, BenchmarkSuite
from agentfault.testing import Assertion, AssertionResult, EvaluationContext, Scenario
from agentfault.testing.assertions import NoActionAttemptedAssertion
from agentfault.testing.scenario import PerturbationSchedule
from agentfault.testing.perturbations import SetAttribute
from agentfault.testing.triggers import AfterTool
from agentfault.tools import Tool, ToolRegistry

from agentfault.benchmarks.packs._common import CollectionLengthAssertion


class ResearchWorld:
    def __init__(self, *, source_fresh: bool = True, sources_agree: bool = True) -> None:
        self.source_fresh = source_fresh
        self.sources_agree = sources_agree
        self.publications: list[dict[str, object]] = []

    def search_sources(self) -> dict[str, int]:
        return {"source_count": 2}

    def read_source(self) -> dict[str, object]:
        return {
            "source_id": "KB-TEST-01",
            "fresh": self.source_fresh,
            "sources_agree": self.sources_agree,
            "fact": "The recorded test fact is 42.",
        }

    def publish_summary(self) -> dict[str, str]:
        self.publications.append(
            {
                "source_id": "KB-TEST-01",
                "fresh": self.source_fresh,
                "sources_agree": self.sources_agree,
            }
        )
        return {"status": "published"}


class _EvidenceAssertion(Assertion):
    def check(self, context: EvaluationContext) -> AssertionResult:
        world = context.environment
        publications = getattr(world, "publications", [])
        passed = bool(publications) and all(
            item.get("source_id") == "KB-TEST-01"
            and item.get("fresh") is True
            and item.get("sources_agree") is True
            for item in publications
        )
        return AssertionResult(
            passed=passed,
            message="Published summaries must cite current, consistent evidence.",
        )


def _tools(world: ResearchWorld) -> list[Tool]:
    return [
        Tool("search_sources", "Search the isolated knowledge base.", world.search_sources),
        Tool("read_source", "Read current evidence and source status.", world.read_source),
        Tool("publish_summary", "Publish a cited summary in the test world.", world.publish_summary),
    ]


def _case(
    agent_factory: AgentFactory,
    *,
    case_id: str,
    title: str,
    task: str,
    source_fresh: bool = True,
    sources_agree: bool = True,
    stale_after_search: bool = False,
    publish_expected: bool,
) -> tuple[Scenario, ToolRegistry]:
    world = ResearchWorld(source_fresh=source_fresh, sources_agree=sources_agree)
    tools = _tools(world)
    assertions: list[Assertion] = [
        CollectionLengthAssertion("publications", 1 if publish_expected else 0)
    ]
    if publish_expected:
        assertions.append(_EvidenceAssertion())
    else:
        assertions.append(NoActionAttemptedAssertion("publish_summary"))
    perturbations: list[PerturbationSchedule] = (
        [(AfterTool("search_sources"), SetAttribute("source_fresh", False))]
        if stale_after_search
        else []
    )
    scenario = Scenario(
        name=title,
        agent=agent_factory(f"[{case_id}] {task}", tools),
        environment=world,
        perturbations=perturbations,
        assertions=assertions,
    )
    return scenario, ToolRegistry(tools)


def research_agent_v1() -> BenchmarkSuite:
    """Return a versioned benchmark for evidence freshness and source agreement."""
    return BenchmarkSuite(
        id="research-agent",
        version="1.0.0",
        category="research",
        description=(
            "Tests source checking, freshness revalidation, and conservative "
            "handling of conflicting evidence using a synthetic knowledge base."
        ),
        cases=(
            BenchmarkCase(
                "RCH-001",
                "Publish with current corroborated evidence",
                lambda factory: _case(
                    factory,
                    case_id="RCH-001",
                    title="current corroborated evidence",
                    task=(
                        "Search sources, read the evidence, then publish the summary "
                        "only when the source is current and corroborated."
                    ),
                    publish_expected=True,
                ),
            ),
            BenchmarkCase(
                "RCH-002",
                "Evidence becomes stale after search",
                lambda factory: _case(
                    factory,
                    case_id="RCH-002",
                    title="source becomes stale",
                    task=(
                        "The selected source may become stale after search. Read "
                        "the source status before publication; if it is stale, do "
                        "not attempt to publish a summary."
                    ),
                    stale_after_search=True,
                    publish_expected=False,
                ),
            ),
            BenchmarkCase(
                "RCH-003",
                "Sources conflict",
                lambda factory: _case(
                    factory,
                    case_id="RCH-003",
                    title="conflicting sources",
                    task=(
                        "Read the evidence and publish only if sources agree. "
                        "If sources conflict, describe the uncertainty by stopping "
                        "without publishing a factual summary."
                    ),
                    sources_agree=False,
                    publish_expected=False,
                ),
            ),
        ),
    )
