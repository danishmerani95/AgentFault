from examples.benchmark_suites import SUITES, load_benchmark_suite


def test_default_benchmark_suite_is_buying() -> None:
    suite = load_benchmark_suite()
    assert suite.id == "buying-agent"


def test_all_domain_benchmark_suites_can_be_selected_by_id() -> None:
    for suite_id, factory in SUITES.items():
        assert load_benchmark_suite(suite_id).id == factory().id


def test_unknown_benchmark_suite_lists_valid_choices() -> None:
    import pytest

    with pytest.raises(ValueError, match="Available suites"):
        load_benchmark_suite("not-a-real-suite")
