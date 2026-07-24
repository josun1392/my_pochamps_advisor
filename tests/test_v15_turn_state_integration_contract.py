"""Pure request-start turn-state baseline; provider and network are not invoked."""
from copy import deepcopy

import llm.advisor_candidate_contract as contract
from core.turn_state import TurnSnapshot


REPOSITORY = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}


def _battle_input():
    return {
        "scenario": {"mode": "advisor", "known_limitations": ["known"]},
        "pokemon": {
            "my_active": {"name_en": "pikachu", "name_ko": "Pikachu", "slot_index": 0, "hp_percent": 62},
            "opponent_active": {"name_en": "eevee", "name_ko": "Eevee", "slot_index": 1, "hp_percent": None},
        },
        "moves": {
            "my_available_moves": [{"slot_index": 0, "move_id": "tackle"}],
            "my_selected_move_index": 0,
        },
    }


def test_request_start_snapshot_is_stable_serializable_and_has_no_token():
    battle = _battle_input()
    selected = [{"move_id": "tackle"}]
    cycle = contract.prepare_ui_recommendation_cycle(
        selected_moves=selected, battle_input=battle, move_repository=REPOSITORY
    )
    assert cycle["status"] == "ready"
    frozen = deepcopy(cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"])
    battle["pokemon"]["my_active"]["name_en"] = "mew"
    battle["moves"]["my_available_moves"][0]["move_id"] = "missing"
    selected[0]["move_id"] = "missing"
    assert cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"] == frozen
    assert TurnSnapshot.from_dict(frozen).to_dict() == frozen
    assert "request_token" not in cycle["recommendation_request"]


def test_active_move_ownership_and_missing_pokemon_block_before_candidate_or_provider_work(monkeypatch):
    evaluated = []
    monkeypatch.setattr(contract, "evaluate_move_slots", lambda **_: evaluated.append(True))
    mismatch = contract.prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "missing"}], battle_input=_battle_input(), move_repository=REPOSITORY
    )
    missing = _battle_input(); missing["pokemon"]["opponent_active"] = {}
    missing_cycle = contract.prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=missing, move_repository=REPOSITORY
    )
    assert mismatch["status"] == "invalid_snapshot"
    assert mismatch["errors"] == ["selected_move_not_owned_by_active_pokemon"]
    assert missing_cycle["errors"] == ["missing_selected_pokemon"]
    assert evaluated == []


def test_unknown_values_are_not_inferred_and_candidate_exact_set_stays_bound_to_snapshot_slots():
    cycle = contract.prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, None], battle_input=_battle_input(), move_repository=REPOSITORY
    )
    snapshot = cycle["recommendation_request"]["battle_snapshot_summary"]["turn_snapshot"]
    player, opponent = snapshot["battle_state"]["active_player"], snapshot["battle_state"]["active_opponent"]
    assert player["side"] == "player" and opponent["side"] == "opponent"
    assert player["known_item_id"] is None and player["item_status"] == "unknown"
    assert opponent["current_hp_percent"] is None
    assert cycle["recommendation_request"]["candidate_exact_set"] == [{"slot_index": 0, "move": "tackle"}]
