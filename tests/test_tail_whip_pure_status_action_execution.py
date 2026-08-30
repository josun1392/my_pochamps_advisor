"""Focused Tail Whip pure-status authority/materialization coverage."""
from __future__ import annotations

from copy import deepcopy

from advisor.canonical_pure_status_action_effect import resolve_canonical_pure_status_action_effect
from llm.advisor_detached_pure_status_action_materializer import materialize_detached_pure_status_action
from llm.advisor_runtime_d0_pure_status_action_execution_authority import freeze_runtime_d0_pure_status_action_execution_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _inputs(stage: int = 0):
    state = _state(); state["opponent_side"]["pokemon"][0]["stat_stages"]["defense"] = stage
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    owner, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = {"move_id":"tail-whip", "category":"status", "target":"selected-pokemon", "accuracy":100, "power":None, "priority":0}
    action = {"action_id":"attack:tail-whip", "action_type":"attack", "identity":"tail-whip", "move_metadata_authority":{"status":"resolved", "move_id":"tail-whip", "metadata":metadata}}
    accuracy = {"status":"resolved", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "actor":owner, "target":target, "action_id":action["action_id"], "move_id":"tail-whip", "outcome":"hit"}
    return state, snapshot, d0, action, owner, target, accuracy


def test_tail_whip_canonical_contract_and_stage_caps():
    for before, after, outcome in ((0, -1, "status_action_applied"), (6, 5, "status_action_applied"), (-5, -6, "status_action_applied"), (-6, -6, "status_action_no_effect")):
        state, snapshot, d0, action, actor, target, accuracy = _inputs(before)
        authority = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, status_accuracy_authority=accuracy)
        assert authority["status"] == "resolved"
        result = materialize_detached_pure_status_action(execution_authority=authority)
        assert (result["outcome"], result["stage_transition"]["pre_stage"], result["stage_transition"]["post_stage"]) == (outcome, before, after)
        assert result["hit_state"] == result["critical_state"] == result["damage_roll"] == "not_applicable"
        assert state["opponent_side"]["pokemon"][0]["stat_stages"]["defense"] == before


def test_tail_whip_fails_closed_and_prevention_is_explicit():
    _, snapshot, d0, action, actor, target, accuracy = _inputs()
    assert resolve_canonical_pure_status_action_effect(move={"move_id":"tackle", "category":"physical", "target":"selected-pokemon"})["status"] == "unsupported"
    missing = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target)
    assert missing["status"] == "incomplete"
    prevention = {**accuracy, "outcome":"prevented"}
    authority = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, prevention_authority=prevention)
    result = materialize_detached_pure_status_action(execution_authority=authority)
    assert result["outcome"] == "status_action_prevented" and result["stage_transition"]["actual_delta"] == 0
    foreign = deepcopy(accuracy); foreign["target"] = actor
    assert freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, status_accuracy_authority=foreign)["status"] == "rejected"


def test_tail_whip_pair_leaf_ledger_and_metrics_are_no_damage():
    _, snapshot, d0, action, actor, target, accuracy = _inputs()
    meta = action["move_metadata_authority"]
    own_meta = {**meta, "candidate_id":action["action_id"], "active_attacker":actor, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"]}
    own = {**action, "move_metadata_authority":own_meta}
    opponent_meta = deepcopy(meta)
    opponent = {"status":"resolved", "action_id":"opponent_attack:tail-whip", "action_type":"attack", "move_id":"tail-whip", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "metadata_authority":opponent_meta, "usability":{"status":"known_usable"}, "selectability":"selectable"}
    opposite = {"status":"resolved", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "actor":target, "target":actor, "action_id":opponent["action_id"], "move_id":"tail-whip", "outcome":"hit"}
    other_action = {"action_id":opponent["action_id"], "action_type":"attack", "identity":"tail-whip", "metadata_authority":opponent_meta}
    left = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=own, actor=actor, target=target, status_accuracy_authority=accuracy)
    right = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=other_action, actor=target, target=actor, status_accuracy_authority=opposite)
    order = {"status":"resolved", "schema_version":"runtime-d0-action-order-authority-v1", "order":"unresolved_tie", "order_engine":{"status":"speed_tie"}, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "own_action_id":own["action_id"], "opponent_action_id":opponent["action_id"], "own_actor":actor, "opponent_actor":target}
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order, pure_status_execution_authorities={own["action_id"]:left, opponent["action_id"]:right})
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator":1,"denominator":1}
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable"
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)
    assert metrics["status"] == "resolved" and metrics["ranking_influence"] == "none"
