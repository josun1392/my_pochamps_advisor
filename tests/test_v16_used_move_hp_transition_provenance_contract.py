from copy import deepcopy

from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input, capture_ui_current_state_provenance


def _battle():
    return {"pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0, "hp_percent": 80}, "opponent_active": {"name_en": "eevee", "slot_index": 1, "hp_percent": 70}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}}


def _owner(side, pokemon, slot, session="s"):
    return {"side": side, "pokemon_id": pokemon, "slot_index": slot, "session_id": session, "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation"}


def _damage(observation_id="o1", **updates):
    value = {"event_kind": "direct_move_damage_observed", "attacker": _owner("self", "pikachu", 0), "defender": _owner("opponent", "eevee", 1), "move_id": None, "move_slot": None, "damage_amount": 30, "hp_unit": "exact", "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation", "observed": True, "confirmed": True, "observation_id": observation_id}
    value.update(updates); return value


def _used(observation_id="o1", **updates):
    value = {"observation_id": observation_id, "attacker": _owner("self", "pikachu", 0), "move_id": "tackle", "move_slot": 0, "source": "ui_used_move_confirmation", "trust": "user_confirmed_observation", "confirmed": True}
    value.update(updates); return value


def _transition(observation_id="o1", **updates):
    value = {"observation_id": observation_id, "defender": _owner("opponent", "eevee", 1), "hp_before": 70, "hp_after": 40, "hp_unit": "exact", "source": "ui_exact_hp_transition_confirmation", "trust": "user_confirmed_observation", "confirmed": True}
    value.update(updates); return value


def _capture(damage, used=(), transition=()):
    return capture_ui_current_state_provenance(_battle(), session_id="s", observed_damage_confirmations=[damage], used_move_confirmations=list(used), hp_transition_confirmations=list(transition))


def test_trusted_used_move_and_exact_transition_complete_one_explicitly_linked_observation():
    captured = _capture(_damage(), [_used()], [_transition()])
    event = captured["observed_damage_context"]["observed_damage_events"][0]
    assert (event["move_id"], event["move_slot"], event["payload"]["mode"]) == ("tackle", 0, "complete")
    assert event["payload"]["derived_damage"] == 30
    frozen = build_turn_snapshot_from_battle_input(captured).to_dict()
    assert frozen["current_state"]["observed_damage_context"] == captured["observed_damage_context"]


def test_selected_candidate_is_not_used_move_and_wrong_or_stale_confirmation_is_excluded():
    amount_only = _capture(_damage())
    assert amount_only["observed_damage_context"]["observed_damage_events"][0]["move_id"] is None
    for invalid in (_used(move_slot=1), _used(attacker=_owner("self", "raichu", 0)), _used(attacker=_owner("self", "pikachu", 0, "old"))):
        assert _capture(_damage(), [invalid])["observed_damage_context"]["observed_damage_events"][0]["move_id"] is None


def test_percent_invalid_or_unlinked_transition_is_not_converted_or_merged_and_mismatch_is_preserved():
    for invalid in (_transition(hp_unit="percent"), _transition(hp_after=71), _transition(hp_before=-1), _transition(observation_id="other")):
        event = _capture(_damage(), transition=[invalid])["observed_damage_context"]["observed_damage_events"][0]
        assert "hp_transition_provenance" not in event
    conflict = _capture(_damage(), transition=[_transition(hp_after=41)])["observed_damage_context"]["observed_damage_events"][0]
    assert conflict["enrichment_status"] == "conflicting_damage_amount" and conflict["damage_amount"] == 30


def test_snapshot_is_detached_and_observed_evidence_never_changes_q12_or_infers_facts():
    used, transition = _used(), _transition()
    captured = _capture(_damage(), [used], [transition])
    frozen = build_turn_snapshot_from_battle_input(captured).to_dict()["current_state"]
    used["move_id"] = "thunderbolt"; transition["hp_after"] = 1
    event = frozen["observed_damage_context"]["observed_damage_events"][0]
    assert event["move_id"] == "tackle" and event["payload"]["hp_after"] == 40
    assert "q12_damage" not in event and "final_stats" not in event and "ability" not in event and "item" not in event
