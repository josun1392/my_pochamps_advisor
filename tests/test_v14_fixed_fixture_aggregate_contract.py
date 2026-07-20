from llm.structured_fixture_evaluation import aggregate_structured_fixture_results, evaluate_structured_fixture, get_fixed_fixture_catalog


def test_aggregate_reports_fixed_fixture_counts_without_provider_or_reliability_claims():
    results = [evaluate_structured_fixture(fixture=fixture) for fixture in get_fixed_fixture_catalog()]
    summary = aggregate_structured_fixture_results(results=results)
    assert summary["fixture_count"] == 10
    assert summary["preparation_ready_count"] == 8 and summary["provider_blocked_count"] == 2
    assert summary["decode_success_count"] == 8 and summary["semantic_success_count"] == 4
    assert summary["exact_pair_success_count"] == 2
    assert summary["failure_distribution"]["invalid_claim"] == 1
