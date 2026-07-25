from copy import deepcopy

from llm.advisor_q12_snapshot_adapter import invoke_existing_q12_from_snapshot
from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    build_snapshot_damage_input,
    build_snapshot_stat_provenance,
    capture_ui_current_state_provenance,
)


class _Repo:
    def get(self, pokemon_id):
        return {"en": pokemon_id, "types_en": ["normal"], "base_stats": {stat: 80 for stat in BASE_STAT_KEYS}, "abilities_en": ["static", "lightning-rod"]}


def _base():
    return {
        "current_state_session_id": "s0",
        "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}},
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
    }


def _ability(side, ability, pokemon, slot, session="s0"):
    return {
        "side": side, "ability": ability, "status": "user_confirmed", "source": "user_confirmed_current_ability",
        "provenance": {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": session, "source": "user_confirmed_current_ability", "trust": "user_confirmed_current"},
    }


def test_confirmed_self_and_opponent_abilities_are_private_structured_snapshot_facts():
    base = _base()
    captured = capture_ui_current_state_provenance(
        base, session_id="s0", ability_confirmations=[
            _ability("self", "static", "pikachu", 0), _ability("opponent", "adaptability", "eevee", 1),
        ],
    )
    assert "ability_context" not in base
    entries = captured["ability_context"]["current_abilities"]
    assert [entry["ability"] for entry in entries] == ["static", "adaptability"]
    snapshot = build_request_start_recommendation_snapshot(captured, selectable_moves=("tackle",))
    bridge = build_snapshot_stat_provenance(snapshot, species_repository=_Repo())
    assert bridge["attacker"]["known_ability"]["value"] == "static"
    assert bridge["defender"]["known_ability"]["value"] == "adaptability"
    frozen = snapshot.to_dict(); captured["ability_context"]["current_abilities"][0]["ability"] = "lightning-rod"
    assert snapshot.to_dict() == frozen


def test_wrong_owner_stale_unknown_and_species_metadata_only_never_become_known():
    base = _base()
    captured = capture_ui_current_state_provenance(
        base, session_id="s0", ability_confirmations=[
            _ability("self", "static", "pikachu", 9),
            _ability("opponent", "adaptability", "eevee", 1, session="old"),
            _ability("self", "unknown", "pikachu", 0),
        ],
    )
    assert "ability_context" not in captured
    snapshot = build_request_start_recommendation_snapshot(base, selectable_moves=("tackle",))
    bridge = build_snapshot_stat_provenance(snapshot, species_repository=_Repo())
    assert bridge["attacker"]["known_ability"]["available"] is False
    assert bridge["defender"]["known_ability"]["available"] is False


def test_observed_event_does_not_create_current_ability_and_q12_keeps_modifier_limited():
    captured = capture_ui_current_state_provenance(
        _base(), session_id="s0", observed_events=[{
            "event_kind": "ability_activation_observed", "side": "self", "status": "user_confirmed",
            "source": "explicit_user_event_confirmation", "confirmed": True, "ability": "static",
        }],
    )
    assert "ability_context" not in captured
    # Existing Q12 invocation remains independent of a known ability identity.
    result = invoke_existing_q12_from_snapshot({"move": {}}, stat_provenance={}, trusted_level=50)
    assert result["status"] == "unavailable"


def test_ability_context_is_detached_from_q12_damage_input_evidence():
    captured = capture_ui_current_state_provenance(
        _base(), session_id="s0", ability_confirmations=[_ability("self", "static", "pikachu", 0)],
    )
    snapshot = build_request_start_recommendation_snapshot(captured, selectable_moves=("tackle",))
    damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id="tackle", selectable_moves=("tackle",), move_metadata={"category": "physical", "power": 40, "type": "normal"})
    frozen = deepcopy(damage)
    captured["ability_context"]["current_abilities"][0]["ability"] = "lightning-rod"
    assert damage == frozen
