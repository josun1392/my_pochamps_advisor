from copy import deepcopy

from llm.advisor_turn_snapshot import (
    BASE_STAT_KEYS,
    build_request_start_recommendation_snapshot,
    capture_ui_current_state_provenance,
)


def _base():
    return {
        "pokemon": {
            "my_active": {"name_en": "pikachu", "slot_index": 0},
            "opponent_active": {"name_en": "eevee", "slot_index": 1},
        },
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
    }


def _entry(side, stat, value, pokemon, slot, session="s0"):
    return {
        "side": side, "stat": stat, "value": value,
        "status": "user_confirmed", "source": "user_confirmed_final_battle_stat",
        "confidence": "known",
        "provenance": {
            "side": side, "slot_index": slot, "pokemon_id": pokemon,
            "session_id": session, "source": "user_confirmed_final_battle_stat",
            "trust": "user_confirmed_current",
        },
    }


def _complete(side, pokemon, slot, session="s0"):
    return [_entry(side, stat, 100 + index, pokemon, slot, session) for index, stat in enumerate(BASE_STAT_KEYS)]


def test_complete_structured_final_stats_are_captured_detached_and_owner_bound():
    source = [*_complete("self", "pikachu", 0), *_complete("opponent", "eevee", 1)]
    base = _base()
    captured = capture_ui_current_state_provenance(
        base, session_id="s0", final_stat_confirmations=source
    )

    assert "final_stat_context" not in base
    entries = captured["final_stat_context"]["current_final_stats"]
    assert len(entries) == 12
    assert entries[0]["provenance"]["pokemon_id"] == "pikachu"
    snapshot = build_request_start_recommendation_snapshot(captured, selectable_moves=("tackle",))
    frozen = snapshot.to_dict()["current_state"]["final_stat_context"]
    source[0]["value"] = 1
    assert frozen["current_final_stats"][0]["value"] == 100


def test_partial_wrong_owner_and_stale_final_stats_are_excluded_not_retagged():
    partial = _complete("self", "pikachu", 0)[:5]
    wrong_slot = _complete("self", "pikachu", 1)
    stale = _complete("opponent", "eevee", 1, session="old")
    captured = capture_ui_current_state_provenance(
        _base(), session_id="s0", final_stat_confirmations=[*partial, *wrong_slot, *stale]
    )

    entries = captured["final_stat_context"]["current_final_stats"]
    assert len(entries) == 5
    assert {entry["stat"] for entry in entries} == set(BASE_STAT_KEYS) - {"speed"}
    assert all(entry["provenance"]["slot_index"] == 0 for entry in entries)
    assert all(entry["provenance"]["session_id"] == "s0" for entry in entries)


def test_invalid_value_or_provenance_free_entry_never_becomes_final_stat_context():
    invalid = _entry("self", "attack", 0, "pikachu", 0)
    free = {key: value for key, value in _entry("self", "defense", 120, "pikachu", 0).items() if key != "provenance"}
    captured = capture_ui_current_state_provenance(
        _base(), session_id="s0", final_stat_confirmations=[invalid, free]
    )

    assert "final_stat_context" not in captured
