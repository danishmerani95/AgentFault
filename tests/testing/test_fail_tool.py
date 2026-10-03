import pytest

from cartspec.testing.perturbations import FailTool
from examples.basic_world import create_basic_world


def test_fail_tool_raises_its_configured_error() -> None:
    with pytest.raises(RuntimeError, match="Injected failure"):
        FailTool("Injected failure").apply(create_basic_world())
