from tests.test_v14_structured_actual_smoke_regression_contract import _stat
import llm.advisor_client as client


def test_smoke_fixture_first_fails_on_resolved_partial_context_contradiction(monkeypatch):
    battle = {"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "self"}, "opponent_active": {"name_en": "opponent"}}, "final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}
    response = {"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [{"kind": "partial_context", "claim": "missing evidence"}], "risks": [], "alternatives": []}
    monkeypatch.setattr(client, "call_structured_recommendation_provider", lambda **_: (response, {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "model": "x", "tool": "structured_recommendation", "success": True, "failure_code": None}))
    result = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "tackle"}], battle_input=battle, move_repository={"tackle": {"category": "physical", "power": 40, "type": "normal"}}, model="x")
    assert result["status"] == "response_validation_failed"
    assert result["errors"] == ["claim_evidence_contradiction"]
