from copy import deepcopy

import llm.advisor_candidate_contract as contract


def _stat(side, stat, value):
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _snapshot():
    return {"final_stat_context": {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150), _stat("self", "special-attack", 200), _stat("opponent", "special-defense", 150), _stat("self", "speed", 200), _stat("opponent", "speed", 100)]}}


def test_valid_prepare_preserves_order_evidence_and_request_exact_sets_without_input_aliasing():
    moves = ["tackle", None, "tackle"]; snapshot = _snapshot(); summary = {"summary": [1]}; limits = ["limited"]
    cycle = contract.prepare_recommendation_cycle(moves=moves, battle_snapshot=snapshot, battle_snapshot_summary=summary, repositories={"tackle": {"category": "physical", "power": 40, "type": "normal"}}, known_limitations=limits)
    moves[0] = "mutated"; snapshot["final_stat_context"]["current_final_stats"][0]["value"] = 0; summary["summary"].append(2); limits.append("mutated")
    assert cycle["status"] == "ready"
    assert [candidate["slot_index"] for candidate in cycle["candidates"]] == [0, 2]
    assert cycle["evidence_bundle"]["battle_snapshot_summary"] == {"summary": [1]}
    assert cycle["recommendation_request"]["candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}, {"slot_index": 2, "move": "tackle"}]
    assert "repositories" not in cycle and cycle["evidence_bundle"]["known_limitations"] == ["limited"]


def test_prepare_nonready_and_sanitized_failure_statuses(monkeypatch):
    empty = contract.prepare_recommendation_cycle(moves=[], battle_snapshot={}, repositories={})
    assert empty["status"] == "no_candidates" and empty["recommendation_request"] is None
    unavailable = contract.prepare_recommendation_cycle(moves=["missing"], battle_snapshot={}, repositories={})
    assert unavailable["status"] == "no_selectable_candidates" and unavailable["recommendation_request"] is None
    invalid = contract.prepare_recommendation_cycle(moves="bad", battle_snapshot={}, repositories={})
    assert invalid["errors"] == ["invalid_move_slots"] and invalid["recommendation_request"] is None
    monkeypatch.setattr(contract, "evaluate_move_slots", lambda **_: (_ for _ in ()).throw(RuntimeError("private")))
    assert contract.prepare_recommendation_cycle(moves=[], battle_snapshot={}, repositories={})["errors"] == ["candidate_evaluation_failed"]


def test_request_refusal_preserves_available_deterministic_evidence(monkeypatch):
    original = contract.build_recommendation_request
    monkeypatch.setattr(contract, "build_recommendation_request", lambda **_: {"readiness": {"status": "invalid_evidence_bundle"}})
    cycle = contract.prepare_recommendation_cycle(moves=["missing"], battle_snapshot={}, repositories={})
    assert cycle["status"] == "request_validation_failed" and cycle["candidates"] and cycle["evidence_bundle"]
    monkeypatch.setattr(contract, "build_recommendation_request", original)
