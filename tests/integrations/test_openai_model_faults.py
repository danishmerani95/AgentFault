from types import SimpleNamespace
from typing import Any

from agentfault.integrations.openai import OpenAIAgent
from agentfault.testing import (
    AfterModelCall,
    BeforeModelCall,
    MalformedModelResponseFault,
    ModelTimeoutFault,
    Scenario,
    ScenarioRunner,
)
from agentfault.testing.triggers import AfterModelCall, BeforeModelCall
from agentfault.tools import ToolRegistry


def _fake_client(response: Any) -> Any:
    def create(**kwargs: Any) -> Any:
        return response

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


def test_openai_agent_exposes_model_fault_boundary_for_scenario_runner() -> None:
    agent = OpenAIAgent(
        system_prompt="test",
        user_prompt="test",
        tools=[],
        model="fixture-model",
        client=_fake_client(None),
    )
    scenario = Scenario(
        name="OpenAI API timeout",
        agent=agent,
        environment={},
        model_faults=[(BeforeModelCall(1), ModelTimeoutFault())],
    )

    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, TimeoutError)
    assert result.trajectory == []


def test_openai_adapter_surfaces_corrupted_model_response_as_execution_error() -> None:
    # The fake successful provider response proves the interceptor can corrupt
    # the response at the actual model-call boundary without network access.
    agent = OpenAIAgent(
        system_prompt="test",
        user_prompt="test",
        tools=[],
        model="fixture-model",
        client=_fake_client(object()),
    )
    scenario = Scenario(
        name="OpenAI response corruption",
        agent=agent,
        environment={},
        model_faults=[(AfterModelCall(1), MalformedModelResponseFault(None))],
    )

    result = ScenarioRunner(ToolRegistry([])).run(scenario)

    assert result.passed is False
    assert isinstance(result.error, AttributeError)
