from copy import deepcopy
from llm.advisor_detached_current_healing_prevented_at_item_check_authority import (
    materialize_detached_current_healing_prevented_at_item_check_authority,
)
from llm.advisor_detached_psychic_noise_healing_prevented_transition import (
    SCHEMA_VERSION,
    attach_detached_psychic_noise_healing_prevented_transitions,
    materialize_detached_psychic_noise_healing_prevented_transition,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_immediate_move_vs_move_action_pair import _normal_formula_ledger
from llm.advisor_substitute import update_substitute_state_context
from tests.test_detached_intermediate_predictive_authority import _metadata_authority, _owner as _complete_owner, _snapshot as _complete_snapshot, _state as _complete_state


def _state():
    state = create_unknown_bootstrap_battle_state("psychic-noise", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state, side):
    pokemon = state[f"{side}_side"]["pokemon"][0]
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": pokemon["pokemon_id"]}


def _inputs():
    state = _state()
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    return state, snapshot, d0, d0["active_owners"]["self"], d0["active_owners"]["opponent"]


def _leaf(d0, attacker, target, *, hit="hit", move="psychic-noise", damage=20, target_hp=80, leaf_id="psychic-hit"):
    bindings = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    return {
        "leaf_id": leaf_id, "candidate_id": "attack:" + move, "action_type": "attack", "branch_path": (hit, leaf_id),
        "probability": {"numerator": 1, "denominator": 1}, "hit_state": hit,
        "consequences": {"damage": damage, "own_final_hp": 100, "target_final_hp": target_hp, "source_hit_context": {"target_routing": "target", "target_pre_hp": 100, "target_post_hp": 100 - damage, "actual_damage": damage}},
        "provenance": {**bindings, "attacker": attacker, "target": target, "move_id": move},
    }


def test_successful_surviving_hit_materializes_bound_hypothetical_transition():
    state, snapshot, d0, attacker, target = _inputs()
    leaf = _leaf(d0, attacker, target)
    before = deepcopy(snapshot)
    result = materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=leaf)
    assert result["status"] == "resolved" and result["schema_version"] == SCHEMA_VERSION
    assert result["outcome"] == "applied" and result["state_after"] == "known_present"
    assert result["recipient"] == target and result["source_leaf_id"] == leaf["leaf_id"] and result["hypothetical"] is True
    assert snapshot == before and state["opponent_side"]["pokemon"][0]["healing_prevented_status"] == {"knowledge": "unknown"}


def test_miss_wrong_move_and_move_id_only_cannot_prove_application():
    _state_value, snapshot, d0, attacker, target = _inputs()
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=_leaf(d0, attacker, target, hit="miss", damage=0, target_hp=100))["status"] == "not_applicable"
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=_leaf(d0, attacker, target, move="tackle"))["status"] == "rejected"
    move_only = _leaf(d0, attacker, target)
    move_only["consequences"].pop("source_hit_context")
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=move_only)["status"] == "not_applicable"
    mismatched = _leaf(d0, attacker, target, target_hp=70)
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=mismatched)["status"] == "rejected"


def test_stale_and_foreign_leaf_bindings_fail_closed():
    _state_value, snapshot, d0, attacker, target = _inputs()
    stale = deepcopy(snapshot); stale["state"]["last_applied_observation_sequence"] = 1; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=stale, source_leaf=_leaf(d0, attacker, target))["status"] == "rejected"
    foreign = _leaf(d0, attacker, target); foreign["provenance"]["target"] = attacker
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=foreign)["status"] == "rejected"
    forged = _leaf(d0, attacker, target); forged["provenance"]["source_branch_fingerprint"] = "foreign"
    assert materialize_detached_psychic_noise_healing_prevented_transition(strategy_d0=d0, runtime_snapshot=snapshot, source_leaf=forged)["status"] == "rejected"


def test_attachment_is_branch_local_and_item_check_accepts_only_successful_transition():
    _state_value, snapshot, d0, attacker, target = _inputs()
    hit, miss = _leaf(d0, attacker, target, leaf_id="hit"), _leaf(d0, attacker, target, hit="miss", damage=0, target_hp=100, leaf_id="miss")
    ledger = {"status": "evaluable", "terminal_leaves": (hit, miss), "terminal_probability_mass": {"numerator": 1, "denominator": 1}}
    attached = attach_detached_psychic_noise_healing_prevented_transitions(strategy_d0=d0, runtime_snapshot=snapshot, ledger=ledger)
    hit_leaf, miss_leaf = attached["terminal_leaves"]
    assert hit_leaf["consequences"]["healing_prevented_transition"]["state_after"] == "known_present"
    assert "healing_prevented_transition" not in miss_leaf["consequences"]
    current = {"status": "resolved", "schema_version": "runtime-d0-current-healing-prevented-authority-v1", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "recipient": target, "state": "known_absent"}
    checked = materialize_detached_current_healing_prevented_at_item_check_authority(strategy_d0=d0, terminal_leaf=hit_leaf, recipient=target, current_healing_prevented_authority=current)
    assert checked["status"] == "resolved" and checked["state"] == "known_present"




def test_normal_formula_psychic_noise_wires_only_successful_leaf_transitions():
    state = _complete_state()
    for side in ("self", "opponent"):
        state["substitute_state_context"] = update_substitute_state_context(
            context=state.get("substitute_state_context"), session_id=state["session_id"],
            owner=_complete_owner(state, side), state="known_inactive", substitute_hp=None,
            provenance="runtime_observed_substitute_state_v1",
        )
    snapshot = _complete_snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_complete_owner(state, "self"))
    metadata = {"move_id": "psychic-noise", "category": "special", "power": 75, "type": "psychic", "accuracy": 100, "priority": 0, "target": "selected-pokemon"}
    authority = _metadata_authority(d0) | {"move_id": "psychic-noise", "metadata": metadata}
    ledger = _normal_formula_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=_complete_owner(state, "self"), target=_complete_owner(state, "opponent"), metadata_authority=authority)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["component_manifest"]["psychic_noise_healing_prevented"]["status"] == "resolved"
    hit_leaves = [leaf for leaf in ledger["terminal_leaves"] if leaf["hit_state"] == "hit" and leaf["consequences"]["target_final_hp"] > 0]
    assert hit_leaves
    assert all(leaf["consequences"]["healing_prevented_transition"]["source_leaf_id"] == leaf["leaf_id"] for leaf in hit_leaves)
    assert all("healing_prevented_transition" not in leaf["consequences"] for leaf in ledger["terminal_leaves"] if leaf["hit_state"] != "hit")
