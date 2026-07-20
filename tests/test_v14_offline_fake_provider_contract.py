import inspect

from llm.advisor_candidate_contract import build_recommendation_request, run_offline_recommendation_provider_adapter
from llm.advisor_client import run_ui_selected_advice


def _prepared():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    evidence = {"battle_snapshot_summary": {}, "candidates": [candidate], "known_limitations": []}
    return {"status": "ready", "candidates": [candidate], "evidence_bundle": evidence, "recommendation_request": build_recommendation_request(evidence_bundle=evidence), "errors": []}


def test_fake_provider_receives_only_approved_payload_and_returns_canonical_response():
    seen = {}
    def fake(payload):
        seen.update(payload); return {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}
    result = run_offline_recommendation_provider_adapter(prepared_cycle=_prepared(), fake_provider=fake)
    assert result["status"] == "provider_response_ready" and result["response_payload"]["recommended_move"] == "move"
    assert set(seen) == {"request_version", "battle_snapshot_summary", "candidate_exact_set", "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails"}
    assert "fake_provider" not in result and "prepare_ui_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)
