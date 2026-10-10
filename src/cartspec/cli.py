import argparse
import json
import sys
from typing import Any

from cartspec.testing import ScenarioResult, ScenarioRunner
from cartspec.testing.scenario_loader import load_scenario_factory


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _result_payload(name: str, result: ScenarioResult) -> dict[str, Any]:
    return {
        "scenario": name,
        "passed": result.passed,
        "assertions": [
            {"passed": item.passed, "message": item.message}
            for item in result.assertions
        ],
        "tool_calls": [
            {
                "name": step.tool_call.name,
                "succeeded": step.succeeded,
                "error": step.error,
            }
            for step in result.trajectory
        ],
        "error": str(result.error) if result.error is not None else None,
    }


def _print_result(name: str, result: ScenarioResult, json_output: bool) -> None:
    payload = _result_payload(name, result)
    if json_output:
        print(json.dumps(payload, indent=2))
        return

    outcome = "PASSED" if result.passed else "FAILED"
    print(f"Scenario: {name}")
    print(f"Result: {outcome}")
    print(f"Assertions: {len(result.assertions)}")
    for assertion in result.assertions:
        marker = "PASS" if assertion.passed else "FAIL"
        print(f"  [{marker}] {assertion.message}")

    failed_calls = sum(not step.succeeded for step in result.trajectory)
    print(
        f"Tool calls: {len(result.trajectory)} total, "
        f"{failed_calls} failed"
    )
    if result.error is not None:
        print(f"Execution error: {result.error}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentfault",
        description="Run AgentFault scenarios from Python factory functions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="run one scenario",
        description=(
            "Run a Python factory in module:function format. The factory must "
            "return a (Scenario, ToolRegistry) tuple."
        ),
    )
    run_parser.add_argument(
        "factory",
        help="scenario factory, for example examples.basic_scenario:build_scenario",
    )
    run_parser.add_argument(
        "--max-steps",
        type=_positive_int,
        default=100,
        help="maximum tool executions (default: 100)",
    )
    run_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="print a machine-readable JSON result",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        scenario, registry = load_scenario_factory(args.factory)
        result = ScenarioRunner(registry, max_steps=args.max_steps).run(scenario)
    except Exception as error:
        print(f"AgentFault: error: {error}", file=sys.stderr)
        return 2

    _print_result(scenario.name, result, args.json_output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
