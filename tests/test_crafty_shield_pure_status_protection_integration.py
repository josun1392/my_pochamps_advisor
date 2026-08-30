"""Focused Crafty Shield/Tail Whip prevention contract."""
from __future__ import annotations

from llm.advisor_runtime_d0_crafty_shield_pure_status_applicability_authority import freeze_runtime_d0_crafty_shield_pure_status_applicability_authority
from llm.advisor_runtime_d0_pure_status_action_execution_authority import freeze_runtime_d0_pure_status_action_execution_authority
from llm.advisor_detached_pure_status_action_materializer import materialize_detached_pure_status_action
from tests.test_tail_whip_pure_status_action_execution import _inputs


def _crafty(d0, guard, incoming, *, success=True, bypass=False):
    return {"session_id": d0["session_id"], "guard_user": guard, "guard_action_id": "opponent_attack:crafty-shield", "incoming_actor": incoming["actor"], "incoming_action_id": incoming["action_id"], "incoming_move_id": incoming["move_id"], "selected_target": incoming["target"], "success": success, "bypass": bypass}


def test_crafty_shield_prevents_tail_whip_without_materializing_stage_change():
    _, snapshot, d0, action, actor, target, accuracy = _inputs(0)
    ordinary = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, status_accuracy_authority=accuracy)
    crafty = freeze_runtime_d0_crafty_shield_pure_status_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=target, guard_action_id="opponent_attack:crafty-shield", incoming_execution_authority=ordinary, protection_context=_crafty(d0, target, ordinary))
    assert crafty["outcome"] == "prevented"
    prevented = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, prevention_authority=crafty)
    leaf = materialize_detached_pure_status_action(execution_authority=prevented)
    assert leaf["outcome"] == "status_action_prevented"
    assert leaf["stage_transition"]["pre_stage"] == leaf["stage_transition"]["post_stage"] == 0
    assert leaf["hit_state"] == leaf["critical_state"] == leaf["damage_roll"] == "not_applicable"


def test_crafty_not_applicable_preserves_ordinary_tail_whip():
    _, snapshot, d0, action, actor, target, accuracy = _inputs(-6)
    ordinary = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, status_accuracy_authority=accuracy)
    crafty = freeze_runtime_d0_crafty_shield_pure_status_applicability_authority(strategy_d0=d0, runtime_snapshot=snapshot, guard_user=target, guard_action_id="opponent_attack:crafty-shield", incoming_execution_authority=ordinary, protection_context=_crafty(d0, target, ordinary, success=False))
    assert crafty["outcome"] == "not_applicable"
    assert materialize_detached_pure_status_action(execution_authority=ordinary)["outcome"] == "status_action_no_effect"
