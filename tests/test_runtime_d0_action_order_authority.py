from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_action_order_authority import freeze_runtime_d0_action_order_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state() -> dict:
    state = create_unknown_bootstrap_battle_state("order-d0", "self-a", "opponent-a")["state"]
    for side, speed in (("self", 120), ("opponent", 100)):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["current_final_stats"] = {
            stat: {"value": value, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}}
            for stat, value in (("attack", 100), ("defense", 100), ("special-attack", 100), ("special-defense", 100), ("speed", speed))
        }
        pokemon["stat_stages"] = {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0}
        pokemon["condition"] = None
        pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
        pokemon["current_ability"] = "static"
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["known_item"] = None
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
        state[f"{side}_side"]["tailwind_status"] = "inactive"
        state[f"{side}_side"]["tailwind_status_provenance"] = {"event_kind": "set_observed_tailwind", "trust": "user_confirmed_observation"}
    state["field"]["trick_room_status"] = "inactive"
    state["field"]["trick_room_status_provenance"] = {"event_kind": "set_observed_trick_room", "trust": "user_confirmed_observation"}
    state["field"]["weather"] = "none"
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["terrain"] = "none"
    state["field"]["terrain_provenance"] = {"event_kind": "current_terrain_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    return state


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _owner(state: dict, side: str) -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _metadata(move: str, *, priority: int = 0) -> dict:
    return {"status": "resolved", "schema_version": "canonical-normalized-move-metadata-authority-v1", "move_id": move, "metadata": {"move_id": move, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": priority}, "provenance": "test"}


def _actions(d0: dict, own_move: str = "tackle", opponent_move: str = "scratch", own_priority: int = 0, opponent_priority: int = 0) -> tuple[dict, dict]:
    own_meta = _metadata(own_move, priority=own_priority)
    own_meta.update({"candidate_id": f"attack:{own_move}", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "active_attacker": d0["decision_owner"]})
    own = {"action_id": f"attack:{own_move}", "action_type": "attack", "identity": own_move, "move_metadata_authority": own_meta}
    opponent = {"schema_version": "runtime-d0-opponent-known-move-action-authority-v1", "action_id": f"opponent_attack:{opponent_move}", "action_type": "attack", "move_id": opponent_move, "opponent_actor": d0["active_owners"]["opponent"], "target_owner": d0["active_owners"]["self"], "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "metadata_authority": _metadata(opponent_move, priority=opponent_priority), "usability": {"status": "incomplete", "reason": "unavailable"}}
    return own, opponent


def _authority(state: dict, **kwargs) -> dict:
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own, opponent = _actions(d0, **kwargs)
    return freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent)


def test_priority_and_speed_order_are_bound_to_d0_not_opponent_usability() -> None:
    priority = _authority(_state(), own_priority=1)
    speed = _authority(_state())
    assert priority["status"] == "resolved" and priority["order"] == "own_first"
    assert priority["opponent_usability"]["status"] == "incomplete"
    assert speed["status"] == "resolved" and speed["order"] == "own_first"
    assert speed["order_engine"]["reason"] == "speed_advantage"


def test_stage_paralysis_tailwind_trick_room_and_choice_scarf_follow_narrow_engine() -> None:
    staged = _state(); staged["self_side"]["pokemon"][0]["stat_stages"]["speed"] = -1
    assert _authority(staged)["order"] == "opponent_first"
    paralyzed = _state(); paralyzed["self_side"]["pokemon"][0]["condition"] = "paralysis"; paralyzed["self_side"]["pokemon"][0]["condition_provenance"]["condition"] = "paralysis"
    assert _authority(paralyzed)["order"] == "opponent_first"
    tailwind = _state(); tailwind["self_side"]["tailwind_status"] = "active"
    assert _authority(tailwind)["order"] == "own_first"
    trick_room = _state(); trick_room["field"]["trick_room_status"] = "active"
    assert _authority(trick_room)["order"] == "opponent_first"
    scarf = _state(); scarf["self_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 80; scarf["self_side"]["pokemon"][0]["known_item"] = "choice-scarf"; scarf["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known"
    assert _authority(scarf)["order"] == "own_first"
    rain = _state(); rain["self_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 80; rain["self_side"]["pokemon"][0]["current_ability"] = "swift-swim"; rain["field"]["weather"] = "rain"
    assert _authority(rain)["order"] == "own_first"


def test_equal_speed_is_explicit_tie_and_unknown_or_unsupported_authority_fails_closed() -> None:
    tied = _state(); tied["opponent_side"]["pokemon"][0]["current_final_stats"]["speed"]["value"] = 120
    result = _authority(tied)
    assert result["status"] == "resolved" and result["order"] == "unresolved_tie"
    unknown = _state(); unknown["field"]["trick_room_status"] = {"knowledge": "unknown"}; unknown["field"].pop("trick_room_status_provenance")
    assert _authority(unknown)["status"] == "incomplete"
    unsupported = _state(); unsupported["self_side"]["pokemon"][0]["known_item"] = "lagging-tail"; unsupported["self_side"]["pokemon"][0]["known_item_provenance"]["status"] = "known"
    assert _authority(unsupported)["status"] == "unsupported"


def test_stale_and_action_binding_mismatches_reject() -> None:
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); own, opponent = _actions(d0)
    stale = deepcopy(state); stale["last_applied_observation_sequence"] = 1
    assert freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=_snapshot(stale), own_action=own, opponent_action=opponent)["status"] == "rejected"
    opponent["target_owner"] = {"wrong": "owner"}
    assert freeze_runtime_d0_action_order_authority(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent)["status"] == "rejected"
