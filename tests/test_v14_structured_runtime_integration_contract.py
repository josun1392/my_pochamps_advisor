from copy import deepcopy

import llm.advisor_client as client


def _stat(side, stat, value): return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}
def _battle(): return {"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "a"}, "opponent_active": {"name_en": "b"}}, "final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}
REPO = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}


def test_structured_runtime_completes_only_validated_response_and_drops_repository(monkeypatch):
    monkeypatch.setattr(client, "call_structured_recommendation_provider", lambda **_: ({"recommendation_status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}, {"input_tokens": 1, "output_tokens": 2, "cached_tokens": 0}))
    moves = [{"move_id": "tackle"}]; battle = _battle()
    result = client.run_structured_ui_recommendation(selected_moves=moves, battle_input=battle, move_repository=REPO, model="m")
    moves[0]["move_id"] = "changed"; battle["pokemon"]["my_active"]["name_en"] = "changed"
    assert result["status"] == "resolved" and result["presentation_model"]["recommended_move"] == "tackle"
    assert "move_repository" not in result and "response_payload" not in result


def test_nonready_and_provider_failure_preserve_prepared_evidence_without_recommendation(monkeypatch):
    called = []
    result = client.run_structured_ui_recommendation(selected_moves=[], battle_input=_battle(), move_repository=REPO, model="m")
    assert result["status"] == "preparation_not_ready" and result["presentation_model"]["recommended_move"] is None
    monkeypatch.setattr(client, "call_structured_recommendation_provider", lambda **_: (_ for _ in ()).throw(client.StructuredProviderError("provider_unavailable")))
    failed = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "tackle"}], battle_input=_battle(), move_repository=REPO, model="m")
    assert failed["status"] == "provider_unavailable" and failed["prepared_cycle"]["evidence_bundle"]
