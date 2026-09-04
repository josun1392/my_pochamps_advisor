from copy import deepcopy

from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_d0_last_executed_move_authority import freeze_runtime_d0_last_executed_move_authority
from llm.advisor_runtime_d0_encore_restriction_authority import freeze_runtime_d0_encore_restriction_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_detached_encore_action_restriction import materialize_detached_encore_application, materialize_encore_forced_execution_action, resolve_encore_move_selectability
from llm.advisor_runtime_d0_encore_locked_move_pp_authority import freeze_runtime_d0_encore_locked_move_pp_authority
from tests.test_runtime_d0_native_damage_context import _state
from tests.test_runtime_d0_opponent_move_usability_authority import _state as _usability_state, _known as _known_opponent_move, _observe as _observe_opponent_move, _owner as _usability_owner, _snapshot as _usability_snapshot


def _owner(state, side="self"):
    p = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": p["pokemon_id"]}
def _plan(state, *steps): return {"session_id": state["session_id"], "status": "planned", "conflicts": [], "replay_policy_version": "v1", "ordered_steps": list(steps)}
def _step(oid, seq, effect, owner, **extra): return {"observation_id": oid, "observation_sequence": seq, "planned_effect": effect, "trust": "user_confirmed_observation", **owner, **extra}
def _snapshot(state): return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _history(state):
    owner = _owner(state, "opponent")
    return project_atomic_transition(state, _plan(state, _step("used-b", 1, "record_executed_move", owner, turn_number=1, move_id="quick-attack", source_action_id="opponent_attack:quick-attack")), state["session_id"])["projected_state"]


def _d0(state):
    snap = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snap, decision_owner=_owner(state))
    return snap, d0


def test_last_executed_move_is_identity_bound_and_missing_is_unknown():
    state = _state("encore-history"); snap, d0 = _d0(state)
    assert freeze_runtime_d0_last_executed_move_authority(strategy_d0=d0, runtime_snapshot=snap, owner=_owner(state, "opponent"))["status"] == "incomplete"
    state = _history(state); snap, d0 = _d0(state)
    history = freeze_runtime_d0_last_executed_move_authority(strategy_d0=d0, runtime_snapshot=snap, owner=_owner(state, "opponent"))
    assert history["status"] == "resolved" and history["move_id"] == "quick-attack"
    assert freeze_runtime_d0_last_executed_move_authority(strategy_d0=d0, runtime_snapshot=snap, owner={**_owner(state, "opponent"), "pokemon_id": "foreign"})["status"] == "rejected"


def test_encore_lifecycle_three_turns_and_switch_retirement():
    state = _history(_state("encore-life")); target = _owner(state, "opponent")
    applied = project_atomic_transition(state, _plan(state, _step("encore-hit", 2, "apply_encore_restriction", target, turn_number=1, source_action_id="attack:encore", source_move_id="encore", locked_move_id="quick-attack", last_used_execution_id="used-b")), state["session_id"])["projected_state"]
    current = applied
    for seq, turn, remaining in ((3, 2, 2), (4, 3, 1), (5, 4, None)):
        current = project_atomic_transition(current, _plan(current, _step(f"done-{turn}", seq, "complete_encore_restricted_active_turn", target, turn_number=turn, completion_kind="affected_active_turn_completed")), current["session_id"])["projected_state"]
        assert current["current_encore_restrictions"]["opponent"]["remaining_target_turns"] == remaining
    assert current["current_encore_restrictions"]["opponent"]["retired_reason"] == "expired"
    duplicate = project_atomic_transition(current, _plan(current, _step("duplicate", 6, "complete_encore_restricted_active_turn", target, turn_number=4, completion_kind="affected_active_turn_completed")), current["session_id"])
    assert duplicate["status"] == "blocked_by_semantic_conflict"


def test_encore_application_and_forced_execution_preserve_selected_intent():
    state = _history(_state("encore-app")); snap, d0 = _d0(state); actor, target = _owner(state), _owner(state, "opponent")
    history = freeze_runtime_d0_last_executed_move_authority(strategy_d0=d0, runtime_snapshot=snap, owner=target)
    bindings = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "actor": actor, "target": target, "action_id": "attack:encore", "move_id": "encore"}
    known = lambda **extra: {"status": "resolved", **bindings, **extra}
    bound_target = {key: d0["session_id"] if key == "session_id" else d0["source_runtime_fingerprint"] if key == "source_runtime_fingerprint" else d0["strategy_preview_fingerprint"] if key == "source_branch_fingerprint" else d0["decision_owner"] for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")} | {"status": "resolved", "owner": target}
    inactive = {**bound_target, "state": "not_active"}
    action = {"action_id": "attack:encore", "identity": "encore", "metadata_authority": {"metadata": {"move_id": "encore", "category": "status", "type": "normal", "accuracy": 100, "priority": 0}}}
    meta = {**bound_target, "metadata": {"move_id": "quick-attack", "category": "physical", "priority": 1}}
    application = materialize_detached_encore_application(strategy_d0=d0, action=action, actor=actor, target=target, accuracy_authority=known(outcome="hit"), last_used_move_authority=history, last_used_move_metadata_authority=meta, last_move_pp_authority={**bound_target, "move_id": "quick-attack", "usable": True}, current_encore_authority=inactive, target_side_ability_authority=known(ability="none"), protection_authority=known(outcome="not_applicable"), reflection_authority=known(outcome="not_applicable"))
    assert application["outcome"] == "applicable"
    forced = materialize_encore_forced_execution_action(selected_action={"action_id": "opponent_attack:tackle", "identity": "tackle"}, actor=target, encore_application=application)
    assert forced["execution_move_id"] == "quick-attack" and forced["execution_priority"] == 1 and forced["selected_move_id"] == "tackle"
    select = resolve_encore_move_selectability(encore_authority={**bound_target, "state": "active", "locked_move_id": "quick-attack"}, owner=target, move_metadata_authority={**meta, "active_attacker": target})
    assert select["selectability"] == "selectable"


def test_encore_pp_bridge_never_infers_unknown_or_other_restriction_as_pp():
    state = _usability_state(); _known_opponent_move(state, "tackle"); snap = _usability_snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snap, decision_owner=_usability_owner(state, "self")); target = _usability_owner(state, "opponent")
    assert freeze_runtime_d0_encore_locked_move_pp_authority(strategy_d0=d0, runtime_snapshot=snap, owner=target, move_id="tackle")["status"] == "incomplete"
    no_pp = _observe_opponent_move(state, "known_unusable", "no_pp")
    snap = _usability_snapshot(no_pp); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snap, decision_owner=_usability_owner(no_pp, "self")); target = _usability_owner(no_pp, "opponent")
    assert freeze_runtime_d0_encore_locked_move_pp_authority(strategy_d0=d0, runtime_snapshot=snap, owner=target, move_id="tackle")["usable"] is False
