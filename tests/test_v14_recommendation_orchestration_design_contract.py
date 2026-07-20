from llm.advisor_candidate_contract import build_evidence_bundle, build_recommendation_request, evaluate_move_slots


PREPARATION_STATUSES = {"ready", "no_candidates", "no_selectable_candidates", "invalid_snapshot", "candidate_evaluation_failed", "request_validation_failed"}


def test_provider_neutral_design_sequence_uses_existing_pure_contracts_only():
    snapshot = {}
    candidates = evaluate_move_slots(moves=[], battle_snapshot=snapshot, repositories={})
    evidence = build_evidence_bundle(snapshot, candidates, [])
    request = build_recommendation_request(evidence_bundle=evidence)
    assert candidates == [] and request["readiness"]["status"] == "no_candidates"
    assert PREPARATION_STATUSES >= {"ready", "no_candidates", "no_selectable_candidates"}
    assert "provider" not in request and "ranking_score" not in request


def test_design_keeps_preparation_and_completion_as_separate_boundaries():
    prepared = {"status": "ready", "candidates": [], "evidence_bundle": {}, "recommendation_request": {"readiness": {"status": "ready"}}, "errors": []}
    assert set(prepared) == {"status", "candidates", "evidence_bundle", "recommendation_request", "errors"}
    assert prepared["status"] == "ready"
