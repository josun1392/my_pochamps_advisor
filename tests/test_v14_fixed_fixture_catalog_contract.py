from llm.structured_fixture_evaluation import get_fixed_fixture_catalog


def test_catalog_is_versioned_sanitized_and_has_explicit_expectations_for_every_category():
    catalog = get_fixed_fixture_catalog()
    required = {"fixture_id", "expected_preparation_status", "expected_selectable_count", "expected_recommendation_status", "expected_semantic_result", "expected_failure_code", "provider_invocation_allowed"}
    ids = {fixture["fixture_id"] for fixture in catalog}
    assert len(catalog) == len(ids) == 10
    assert ids == {"clear_resolved", "close_resolved", "insufficient_context", "no_selectable_candidates", "invalid_alternative", "slot_mismatch", "unsupported_claim", "partial_context_valid", "partial_context_contradiction", "no_usable_candidate"}
    assert all(required <= set(fixture) for fixture in catalog)
    assert all("raw_response" not in str(fixture) and "api_key" not in str(fixture).lower() for fixture in catalog)


def test_catalog_returns_independent_fixture_copies():
    first = get_fixed_fixture_catalog()
    second = get_fixed_fixture_catalog()
    first[0]["selected_moves"][0]["move_id"] = "mutated"
    assert second[0]["selected_moves"][0]["move_id"] == "tackle"
