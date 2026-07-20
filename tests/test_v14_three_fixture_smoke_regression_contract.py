"""Sanitized v14.15 three-fixture outcomes; no provider access."""

import llm.advisor_client as client


def _battle(*, resolved=False):
    battle = {
        "scenario": {"mode": "advisor", "known_limitations": ["trusted limitation"]},
        "pokemon": {"my_active": {"name_en": "self"}, "opponent_active": {"name_en": "opponent"}},
    }
    if resolved:
        def stat(side, name, value):
            return {"side": side, "stat": name, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}
        battle["final_stat_context"] = {"current_final_stats": [
            stat("self", "attack", 200), stat("self", "special-attack", 200), stat("self", "speed", 200),
            stat("opponent", "defense", 150), stat("opponent", "special-defense", 150), stat("opponent", "speed", 100),
        ]}
    return battle


def _repository():
    return {
        "tackle": {"category": "physical", "power": 40, "type": "normal"},
        "hyper-beam": {"category": "special", "power": 150, "type": "normal"},
    }


def _response(status, *, reasons=None):
    return {
        "recommendation_status": status,
        "recommended_move": "hyper-beam" if status == "resolved" else None,
        "recommended_slot_index": 1 if status == "resolved" else None,
        "primary_reasons": [] if reasons is None else reasons,
        "risks": [],
        "alternatives": [],
    }


def _usage():
    return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "model": "sanitized", "tool": "structured_recommendation", "success": True, "failure_code": None}


def test_sanitized_three_fixture_outcomes_preserve_evidence_without_raw_provider_data(monkeypatch):
    responses = iter((_response("resolved"), _response("insufficient_context", reasons=[{"kind": "unsupported", "claim": "sanitized"}])) )
    calls = []

    def fake_provider(**_):
        calls.append("called")
        return next(responses), _usage()

    monkeypatch.setattr(client, "call_structured_recommendation_provider", fake_provider)
    resolved = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "tackle"}, {"move_id": "hyper-beam"}], battle_input=_battle(resolved=True), move_repository=_repository(), model="sanitized")
    insufficient = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "tackle"}, {"move_id": "hyper-beam"}], battle_input=_battle(), move_repository=_repository(), model="sanitized")
    blocked = client.run_structured_ui_recommendation(selected_moves=[{"move_id": "missing-a"}, {"move_id": "missing-b"}], battle_input=_battle(), move_repository={}, model="sanitized")

    assert len(calls) == 2 <= 3
    assert resolved["status"] == "resolved" and resolved["presentation_model"]["recommended_slot_index"] == 1
    assert insufficient["status"] == "response_validation_failed" and insufficient["errors"] == ["invalid_claim"]
    assert blocked["status"] == "preparation_not_ready" and blocked["prepared_cycle"]["status"] == "no_selectable_candidates"
    for result in (resolved, insufficient, blocked):
        assert "response_payload" not in result and "raw_response" not in result and result["prepared_cycle"].get("evidence_bundle") is not None
