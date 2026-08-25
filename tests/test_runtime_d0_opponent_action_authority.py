from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_opponent_action_authority import (
    METADATA_SCHEMA_VERSION,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state() -> dict:
    return create_unknown_bootstrap_battle_state("opponent-action-d0", "self-a", "opponent-a")["state"]


def _owner(state: dict, side: str) -> dict:
    slot = state[f"{side}_side"]["active_slot_index"]
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _metadata(move: str, **overrides) -> dict:
    payload = {"move_id": move, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0, **overrides}
    return {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": payload, "provenance": "repository_normalized_move_metadata_v1"}


def _known(state: dict, *moves: str) -> None:
    owner = _owner(state, "opponent")
    pokemon = state["opponent_side"]["pokemon"][owner["slot_index"]]
    pokemon["known_move_ids"] = list(moves)
    pokemon["known_move_ids_provenance"] = {
        move: {"event_kind": "used_move_observed", "trust": "user_confirmed_observation", "source_observation_id": f"obs-{index}", "source_sequence": index}
        for index, move in enumerate(moves, 1)
    }


def _authority(state: dict, metadata: dict) -> dict:
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities=metadata)


def test_observed_identity_bound_moves_become_distinct_d0_actions_but_not_selectable() -> None:
    state = _state(); _known(state, "tackle", "quick-attack")
    result = _authority(state, {"tackle": _metadata("tackle"), "quick-attack": _metadata("quick-attack", priority=1)})

    assert result["status"] == "resolved"
    assert result["known_moveset_state"] == "partially_known"
    assert result["unknown_move_slots"] == 2
    assert [row["action_id"] for row in result["actions"]] == ["opponent_attack:tackle", "opponent_attack:quick-attack"]
    assert all(row["status"] == "resolved" and row["selectability"] == "unknown" for row in result["actions"])
    assert all(row["usability"]["status"] == "incomplete" for row in result["actions"])
    assert result["actions"][0]["metadata_authority"]["metadata"]["power"] == 40


def test_unknown_or_unproven_known_moves_do_not_become_actions() -> None:
    unknown = _authority(_state(), {})
    assert unknown["status"] == "incomplete" and unknown["actions"] == ()

    state = _state(); state["opponent_side"]["pokemon"][0]["known_move_ids"] = ["tackle"]
    unproven = _authority(state, {"tackle": _metadata("tackle")})
    assert unproven["status"] == "incomplete"
    assert unproven["reason"] == "opponent_known_move_provenance_unavailable"


def test_metadata_is_required_and_conflicts_fail_closed() -> None:
    state = _state(); _known(state, "tackle")
    missing = _authority(state, {})
    assert missing["status"] == "resolved"
    assert missing["actions"][0]["status"] == "incomplete"

    conflict = _authority(state, {"tackle": _metadata("scratch")})
    assert conflict["actions"][0]["status"] == "rejected"
    assert conflict["actions"][0]["reason"] == "canonical_opponent_move_metadata_binding_conflict"


def test_complete_moveset_and_fresh_active_identity_are_bound_strictly() -> None:
    state = _state(); _known(state, "tackle", "scratch", "growl", "tail-whip")
    metadata = {move: _metadata(move, category="status", power=None) for move in ("growl", "tail-whip")}
    metadata.update({"tackle": _metadata("tackle"), "scratch": _metadata("scratch")})
    result = _authority(state, metadata)
    assert result["status"] == "resolved" and result["known_moveset_state"] == "complete" and result["unknown_move_slots"] == 0

    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    changed = deepcopy(state); changed["opponent_side"]["pokemon"][0]["pokemon_id"] = "other"
    stale = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=_snapshot(changed), canonical_move_metadata_authorities=metadata)
    assert stale["status"] == "rejected"


def test_source_is_detached_and_never_creates_opponent_action_probabilities() -> None:
    state = _state(); _known(state, "tackle")
    result = _authority(state, {"tackle": _metadata("tackle")})
    state["opponent_side"]["pokemon"][0]["known_move_ids"].append("scratch")

    assert [row["move_id"] for row in result["actions"]] == ["tackle"]
    assert "probability" not in repr(result)
