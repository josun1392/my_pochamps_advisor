from copy import deepcopy

import pytest

from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle
from llm.advisor_turn_snapshot import (
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    capture_ui_current_state_provenance,
)


def _battle_input():
    return {
        "pokemon": {
            "my_active": {"name_en": "pikachu", "slot_index": 0},
            "opponent_active": {"name_en": "eevee", "slot_index": 1},
        },
        "moves": {
            "my_selected_move": {"move_id": "tackle"},
            "my_available_moves": [{"slot_index": 0, "move_id": "tackle"}],
        },
        "current_hp_context": {"current_hp": [{"side": "self", "current_hp": 50}]},
        "field_state_context": {"current_field": {"weather": "rain"}},
    }


def _snapshot_with_event():
    captured = capture_ui_current_state_provenance(
        _battle_input(),
        session_id="ui-session-0",
        observed_events=[{
            "side": "self", "item": "focus-sash",
            "event_type": "item_activation_observed", "status": "user_confirmed",
        }],
    )
    return build_request_start_recommendation_snapshot(
        captured, selectable_moves=("tackle",)
    )


def test_damage_input_is_detached_and_aligned_to_frozen_candidate_identity():
    snapshot = _snapshot_with_event()
    metadata = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "nested": {"power": 40}}
    damage_input = build_snapshot_damage_input(
        snapshot, candidate_slot_index=0, candidate_move_id="tackle",
        selectable_moves=("tackle",), move_metadata=metadata,
    )

    assert damage_input["attacker"]["species_id"] == "pikachu"
    assert damage_input["defender"]["species_id"] == "eevee"
    assert damage_input["move"]["owner_species_id"] == "pikachu"
    assert damage_input["move"]["slot_index"] == 0
    assert damage_input["attacker"]["session_id"] == "ui-session-0"
    assert damage_input["battle_context"]["observed_event_evidence"][0]["payload"]["item"] == "focus-sash"
    assert any("Exact damage guarantee unavailable" in limit for limit in damage_input["calculation_limits"])

    frozen = deepcopy(damage_input)
    metadata["nested"]["power"] = 999
    assert damage_input == frozen


def test_damage_input_rejects_wrong_candidate_and_never_fabricates_final_stats():
    snapshot = _snapshot_with_event()
    with pytest.raises(ValueError, match="candidate_not_owned_by_snapshot"):
        build_snapshot_damage_input(
            snapshot, candidate_slot_index=0, candidate_move_id="thunderbolt",
            selectable_moves=("tackle",), move_metadata={"move_id": "thunderbolt"},
        )

    damage_input = build_snapshot_damage_input(
        snapshot, candidate_slot_index=0, candidate_move_id="tackle",
        selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40},
    )
    assert "final_stats" not in damage_input["attacker"]
    assert "item_activation_observed" in str(damage_input["battle_context"]["observed_event_evidence"])
    assert "known_item" not in damage_input["battle_context"]


def test_ui_candidate_path_uses_snapshot_signature_without_public_payload_changes():
    battle = _battle_input()
    cycle = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}],
        battle_input=battle,
        move_repository={"tackle": {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal"}},
    )

    assert cycle["status"] in {"ready", "no_selectable_candidates", "request_validation_failed"}
    assert "turn_snapshot" not in battle
    assert "session_id" not in battle["pokemon"]["my_active"]
