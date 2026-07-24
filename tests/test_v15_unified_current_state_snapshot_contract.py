"""Pure v15.1 current-state capture contract; no provider factory is reached."""
from copy import deepcopy

import llm.advisor_candidate_contract as contract
from core.turn_state import TurnSnapshot


REPOSITORY = {"facade": {"category": "physical", "power": 70, "type": "normal"}}


def _battle():
    return {
        "scenario": {"mode": "advisor", "known_limitations": []}, "current_state_session_id": "session-a",
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0, "hp_percent": 62}, "opponent_active": {"name_en": "eevee", "slot_index": 1, "hp_percent": 44}},
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "facade"}]},
        "current_hp_context": {"current_hp": [{"side": "self", "slot_index": 0, "current_hp": 62, "maximum_hp": 100}]},
        "condition_context": {"current_conditions": [{"side": "self", "slot_index": 0, "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"}]},
        "ability_context": {"current_abilities": [{"side": "opponent", "slot_index": 1, "ability": "unknown", "status": "user_confirmed", "source": "user_confirmed_current_ability"}]},
        "field_state_context": {"current_field": {"weather": "rain", "terrain": "unknown"}},
        "item_event_context": {"observed_item_events": [{"side": "opponent", "slot_index": 1, "session_id": "session-a", "item": "focus-sash", "event_type": "item_activation_observed", "status": "user_confirmed", "source": "explicit_user_event_confirmation"}]},
    }


def _cycle(battle):
    return contract.prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "facade"}], battle_input=battle, move_repository=REPOSITORY)


def test_rich_current_state_is_frozen_for_candidate_and_provider_summary():
    battle = _battle(); cycle = _cycle(battle)
    assert cycle["status"] == "ready"
    summary = cycle["recommendation_request"]["battle_snapshot_summary"]
    frozen = deepcopy(summary["turn_snapshot"]["current_state"])
    battle["current_hp_context"]["current_hp"][0]["current_hp"] = 1
    battle["condition_context"]["current_conditions"][0]["condition_type"] = "sleep"
    battle["field_state_context"]["current_field"]["weather"] = "sun"
    battle["item_event_context"]["observed_item_events"][0]["item"] = "leftovers"
    assert summary["turn_snapshot"]["current_state"] == frozen
    assert cycle["evidence_bundle"]["battle_snapshot_summary"]["turn_snapshot"]["current_state"] == frozen
    assert TurnSnapshot.from_dict(summary["turn_snapshot"]).to_dict() == summary["turn_snapshot"]
    assert "request_token" not in cycle["recommendation_request"] and "fingerprint" not in cycle["recommendation_request"]


def test_side_slot_and_session_mismatches_block_before_candidate_or_provider_work(monkeypatch):
    evaluated = []
    monkeypatch.setattr(contract, "evaluate_move_slots", lambda **_: evaluated.append(True))
    for mutate in (
        lambda battle: battle["current_hp_context"]["current_hp"][0].update(slot_index=9),
        lambda battle: battle["ability_context"]["current_abilities"][0].update(side="bench"),
        lambda battle: battle["item_event_context"]["observed_item_events"][0].update(session_id="old-session"),
    ):
        battle = _battle(); mutate(battle); cycle = _cycle(battle)
        assert cycle["status"] == "invalid_snapshot"
        assert cycle["errors"] == ["invalid_current_state_ownership"]
    assert evaluated == []


def test_unknown_is_preserved_without_inference_and_snapshot_context_drives_candidate_input(monkeypatch):
    captured = []; original = contract.evaluate_move_slots
    def observe(**kwargs):
        captured.append(deepcopy(kwargs["battle_snapshot"]))
        return original(**kwargs)
    monkeypatch.setattr(contract, "evaluate_move_slots", observe)
    cycle = _cycle(_battle())
    current_state = cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"]["current_state"]
    assert current_state["ability_context"]["current_abilities"][0]["ability"] == "unknown"
    assert current_state["field_state_context"]["current_field"]["terrain"] == "unknown"
    assert captured[0]["current_hp_context"] == current_state["current_hp_context"]
    assert captured[0]["condition_context"] == current_state["condition_context"]
