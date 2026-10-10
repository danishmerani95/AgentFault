from typing import Any

import pytest

from cartspec.testing.scenario_loader import load_scenario_factory
from cartspec.testing.scenario_result import ScenarioResult
from cartspec.testing.scenario_runner import ScenarioRunner


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "agentfault(factory, max_steps=100): run an AgentFault scenario factory",
    )


def _factory_reference(marker: pytest.Mark) -> tuple[str, int]:
    kwargs: dict[str, Any] = dict(marker.kwargs)
    unknown_kwargs = set(kwargs) - {"factory", "max_steps"}
    if unknown_kwargs:
        unknown = ", ".join(sorted(unknown_kwargs))
        raise ValueError(f"Unsupported agentfault marker keyword(s): {unknown}.")

    positional_factory: str | None = None
    if marker.args:
        if len(marker.args) != 1:
            raise ValueError(
                "Use @pytest.mark.agentfault('module:function') with one factory."
            )
        positional_factory = marker.args[0]

    keyword_factory = kwargs.get("factory")
    if positional_factory is not None and keyword_factory is not None:
        raise ValueError("Specify the scenario factory either positionally or by name.")
    reference = positional_factory if positional_factory is not None else keyword_factory
    if not isinstance(reference, str) or not reference:
        raise ValueError(
            "A scenario factory is required, e.g. "
            "@pytest.mark.agentfault('examples.basic_scenario:build_scenario')."
        )

    max_steps = kwargs.get("max_steps", 100)
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
        raise ValueError("agentfault max_steps must be a positive integer.")

    return reference, max_steps


@pytest.fixture
def agentfault_result(request: pytest.FixtureRequest) -> ScenarioResult:
    """Run the scenario factory declared with @pytest.mark.agentfault(...)."""
    marker = request.node.get_closest_marker("agentfault")
    if marker is None:
        pytest.fail(
            "agentfault_result requires @pytest.mark.agentfault('module:function').",
            pytrace=False,
        )

    try:
        reference, max_steps = _factory_reference(marker)
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)

    scenario, registry = load_scenario_factory(reference)
    return ScenarioRunner(registry, max_steps=max_steps).run(scenario)
