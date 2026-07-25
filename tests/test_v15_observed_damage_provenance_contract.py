from copy import deepcopy

from llm.advisor_turn_snapshot import (
    build_turn_snapshot_from_battle_input,
    capture_ui_current_state_provenance,
)


def _battle(session="s0"):
    return {"current_state_session_id": session, "pokemon": {
        "my_active": {"name_en": "pikachu", "slot_index": 0, "hp_percent": 62},
        "opponent_active": {"name_en": "eevee", "slot_index": 1, "hp_percent": 44},
    }, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]}}


def _owner(side, pokemon, slot, session="s0"):
    return {"side": side, "pokemon_id": pokemon, "slot_index": slot, "session_id": session,
            "source": "ui_observed_damage_confirmation", "trust": "user_confirmed_observation"}


def _damage(**changes):
    event = {"event_kind": "direct_move_damage_observed", "attacker": _owner("opponent", "eevee", 1),
             "defender": _owner("self", "pikachu", 0), "move_id": None, "move_slot": None,
             "damage_amount": 31, "hp_unit": "exact", "source": "ui_observed_damage_confirmation",
             "trust": "user_confirmed_observation", "observed": True, "confirmed": True}
    event.update(changes)
    return event


def _events(events, session="s0"):
    captured = capture_ui_current_state_provenance(_battle(session), session_id=session, observed_damage_confirmations=events)
    return captured.get("observed_damage_context", {}).get("observed_damage_events", [])


def test_valid_amount_only_damage_is_canonical_detached_and_move_unavailable():
    raw = _damage()
    captured = capture_ui_current_state_provenance(_battle(), session_id="s0", observed_damage_confirmations=[raw])
    event = captured["observed_damage_context"]["observed_damage_events"][0]
    assert event["source"] == "ui_observed_damage_confirmation" and event["trust"] == "user_confirmed_observation"
    assert event["move_id"] is event["move_slot"] is None
    assert event["payload"] == {"damage_amount": 31, "hp_unit": "exact", "mode": "amount_only"}
    raw["damage_amount"] = 1
    assert build_turn_snapshot_from_battle_input(captured).to_dict()["current_state"]["observed_damage_context"]["observed_damage_events"][0]["payload"]["damage_amount"] == 31


def test_wrong_owner_stale_invalid_transition_and_percent_are_excluded_without_retagging():
    invalid_transition = _damage(hp_before=40, hp_after=41)
    percent = _damage(hp_unit="percent")
    assert _events([_damage(attacker=_owner("opponent", "eevee", 0)), _damage(defender=_owner("self", "raichu", 0)), _damage(attacker=_owner("opponent", "eevee", 1, "old")), invalid_transition, percent]) == []


def test_exact_duplicate_collapses_but_distinct_amounts_remain_and_q12_is_not_overwritten():
    events = _events([_damage(), deepcopy(_damage()), _damage(damage_amount=32)])
    assert [event["payload"]["damage_amount"] for event in events] == [31, 32]
    # The event contains no calculated-damage/Q12 field and cannot become one.
    assert all("q12_damage" not in event and "final_stats" not in event for event in events)


def test_untrusted_move_is_not_associated_and_session_switch_excludes_previous_event():
    assert _events([_damage(move_id="tackle")]) == []
    assert _events([_damage()], session="s1") == []
