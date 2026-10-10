from importlib import import_module
from typing import Any

from agentfault.testing.scenario import Scenario
from agentfault.tools import ToolRegistry


def load_scenario_factory(reference: str) -> tuple[Scenario, ToolRegistry]:
    """Import and call a module:function factory returning (Scenario, ToolRegistry)."""
    module_name, separator, factory_name = reference.partition(":")
    if not separator or not module_name or not factory_name:
        raise ValueError(
            "Scenario factory must use 'module.path:function_name' format."
        )

    module = import_module(module_name)
    factory: Any = getattr(module, factory_name, None)
    if not callable(factory):
        raise ValueError(
            f"Scenario factory {reference!r} does not identify a callable."
        )

    created = factory()
    if not isinstance(created, tuple) or len(created) != 2:
        raise TypeError(
            f"Scenario factory {reference!r} must return (Scenario, ToolRegistry)."
        )

    scenario, tool_registry = created
    if not isinstance(scenario, Scenario):
        raise TypeError(
            f"Scenario factory {reference!r} returned "
            f"{type(scenario).__name__}, expected Scenario."
        )
    if not isinstance(tool_registry, ToolRegistry):
        raise TypeError(
            f"Scenario factory {reference!r} returned "
            f"{type(tool_registry).__name__} as its second value, "
            "expected ToolRegistry."
        )

    return scenario, tool_registry
