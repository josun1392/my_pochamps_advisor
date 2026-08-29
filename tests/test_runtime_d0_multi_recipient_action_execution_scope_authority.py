from copy import deepcopy

from advisor.canonical_multi_recipient_action_execution import canonical_multi_recipient_action_execution_metadata
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import DOUBLES_ACTIVE_TOPOLOGY_SOURCE, SELECTED_ACTION_TARGETING_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_runtime_d0_doubles_action_target_set_authority import freeze_runtime_d0_doubles_action_target_set_authority
from llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority import SCHEMA_VERSION, freeze_runtime_d0_multi_recipient_action_execution_scope_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state(*, battle_format="doubles"):
    state = create_unknown_bootstrap_battle_state("scope", "self-a", "opponent-a", battle_format={"battle_format": battle_format, "source": "user_confirmed_battle_format"})["state"]
    for side in ("self", "opponent"):
        roster = state[f"{side}_side"]["pokemon"]; roster[0].update(current_hp=100, max_hp=100, fainted=False)
        roster[1] = deepcopy(roster[0]); roster[1]["pokemon_id"] = f"{side}-b"
    return state


def _owner(state, side, slot=0):
    return {"session_id": state["session_id"], "side": side, "slot_index": slot, "pokemon_id": state[f"{side}_side"]["pokemon"][slot]["pokemon_id"]}


def _snapshot(state): return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _action(d0, *, move_id="rock-slide", target="all-opponents"):
    metadata = {"move_id": move_id, "category": "physical", "power": 75, "type": "rock", "accuracy": 90, "priority": 0, "target": target}
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": metadata, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


def _observations(state):
    boundary = LifecycleConfirmationBoundary(state["session_id"], {side: _owner(state, side) for side in ("self", "opponent")})
    topology = boundary.confirm(event_kind="doubles_active_topology_observed", payload={"active_owners": [{"side": side, "active_slot_index": slot, "pokemon_id": _owner(state, side, slot)["pokemon_id"], "active": True} for side in ("self", "opponent") for slot in (0, 1)]}, session_id=state["session_id"], source=DOUBLES_ACTIVE_TOPOLOGY_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=1)["observation"]
    targeting = boundary.confirm(event_kind="selected_action_targeting_observed", payload={"decision_point": "turn:1", "action_id": "attack:rock-slide", "move_id": "rock-slide", "selected_target": None}, session_id=state["session_id"], source=SELECTED_ACTION_TARGETING_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="self-a", turn_number=1)["observation"]
    result = project_atomic_transition(state, build_replay_plan(state, [topology, targeting]), state["session_id"])
    assert result["status"] == "ready_with_projected_state", result
    return result["projected_state"]


def _authorities(state):
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); action = _action(d0)
    target_set = freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, acting_owner=_owner(state, "self"), decision_point="turn:1")
    return snapshot, d0, action, target_set


def _freeze(state, *, action=None, target_set=None):
    snapshot, d0, normal, frozen_target_set = _authorities(state)
    return freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action or normal, decision_point="turn:1", target_set_authority=target_set or frozen_target_set)


def test_rock_slide_exposes_exact_recipient_local_execution_scopes_without_graphs():
    state = _observations(_state()); before = deepcopy(state)
    result = _freeze(state)
    assert result["status"] == "resolved" and result["schema_version"] == SCHEMA_VERSION
    assert result["move_id"] == "rock-slide" and result["recipient_resolution_order"] == "frozen_target_set_order"
    assert [(row["side"], row["active_slot_index"]) for row in result["recipients"]] == [("opponent", 0), ("opponent", 1)]
    assert result["spread_damage_modifier_authority"] == {"status": "resolved", "numerator": 3, "denominator": 4, "applies_when_recipient_count_at_least": 2, "provenance": "canonical_multi_recipient_action_execution_scope_v1"}
    assert (result["accuracy_uncertainty_scope"], result["critical_hit_uncertainty_scope"], result["damage_roll_uncertainty_scope"]) == ("recipient_local", "recipient_local", "recipient_local")
    assert "terminal_leaf_roots" not in result and state == before


def test_missing_or_foreign_target_set_and_metadata_mismatches_fail_closed():
    state = _observations(_state()); snapshot, d0, action, target_set = _authorities(state)
    missing = freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority={})
    assert missing["status"] == "incomplete"
    foreign = deepcopy(target_set); foreign["action_id"] = "other"
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=foreign)["status"] == "rejected"
    bad_action = deepcopy(action); bad_action["move_metadata_authority"]["metadata"]["target"] = "selected-pokemon"
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=bad_action, decision_point="turn:1", target_set_authority=target_set)["status"] == "rejected"


def test_stale_d0_and_singles_target_sets_do_not_resolve():
    state = _observations(_state()); snapshot, d0, action, target_set = _authorities(state)
    stale = deepcopy(state); stale["self_side"]["pokemon"][0]["current_hp"] = 99
    stale_snapshot = _snapshot(stale)
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=stale_snapshot, action=action, decision_point="turn:1", target_set_authority=target_set)["status"] == "rejected"
    singles = _state(battle_format="singles")
    snapshot = _snapshot(singles); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(singles, "self")); action = _action(d0)
    target_set = freeze_runtime_d0_doubles_action_target_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, acting_owner=_owner(singles, "self"), decision_point="turn:1")
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=target_set)["status"] == "incomplete"


def test_missing_rng_scope_is_incomplete_and_recipient_order_conflict_rejects(monkeypatch):
    state = _observations(_state()); snapshot, d0, action, target_set = _authorities(state)
    reversed_recipients = deepcopy(target_set)
    reversed_recipients["recipients"] = tuple(reversed(reversed_recipients["recipients"]))
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=reversed_recipients)["status"] == "rejected"
    incomplete_metadata = canonical_multi_recipient_action_execution_metadata("rock-slide")
    incomplete_metadata["damage_roll_uncertainty_scope"] = None
    monkeypatch.setattr(
        "llm.advisor_runtime_d0_multi_recipient_action_execution_scope_authority.canonical_multi_recipient_action_execution_metadata",
        lambda move_id: incomplete_metadata if move_id == "rock-slide" else None,
    )
    assert freeze_runtime_d0_multi_recipient_action_execution_scope_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, decision_point="turn:1", target_set_authority=target_set)["status"] == "incomplete"
