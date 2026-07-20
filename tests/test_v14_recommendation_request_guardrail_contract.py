from llm.advisor_candidate_contract import build_recommendation_request


def _bundle(candidates):
    return {"battle_snapshot_summary": {}, "candidates": candidates, "known_limitations": ["offline limitation"]}


def _candidate(status="partial", availability="partially_evaluable"):
    return {"slot_index": 0, "move": "protect", "status": status, "availability": availability,
            "damage": {"status": "not_applicable"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}


def test_guardrails_are_true_and_request_stays_provider_neutral():
    request = build_recommendation_request(evidence_bundle=_bundle([_candidate()]))
    assert all(request["guardrails"].values())
    forbidden = {"ranking_score", "automatic_winner", "provider", "model", "network", "raw_prompt", "raw_response"}
    assert not (forbidden & set(request))
    assert request["known_limitations"] == ["offline limitation"]


def test_non_ready_evidence_never_creates_a_provider_ready_request():
    cases = [
        build_recommendation_request(evidence_bundle=_bundle([])),
        build_recommendation_request(evidence_bundle=_bundle([_candidate("unavailable", "unavailable")])),
        build_recommendation_request(evidence_bundle={"candidates": []}),
    ]
    assert [request["readiness"]["status"] for request in cases] == ["no_candidates", "no_selectable_candidates", "invalid_evidence_bundle"]
    assert all(request["readiness"]["status"] != "ready" for request in cases)
