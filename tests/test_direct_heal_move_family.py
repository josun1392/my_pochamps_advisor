from __future__ import annotations

from advisor.canonical_direct_heal_move_family import resolve_canonical_direct_heal_move
from llm.advisor_detached_direct_heal_materializer import materialize_detached_direct_heal
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _inputs(current=101, maximum=301):
    state = _state(); state["self_side"]["pokemon"][0].update(current_hp=current, max_hp=maximum, fainted=current == 0)
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actor = d0["active_owners"]["self"]
    metadata = {"move_id":"recover", "category":"status", "target":"self", "priority":0, "accuracy":None, "power":None}
    action = {"action_id":"attack:recover", "action_type":"attack", "identity":"recover", "move_metadata_authority":{"status":"resolved", "metadata":metadata}}
    return snapshot, d0, actor, action


def test_catalog_is_closed_and_metadata_is_exact():
    for move_id in ("recover", "slack-off", "soft-boiled"):
        assert resolve_canonical_direct_heal_move(move={"move_id":move_id, "category":"status", "target":"self", "priority":0, "accuracy":None, "power":None})["status"] == "resolved"
    assert resolve_canonical_direct_heal_move(move={"move_id":"synthesis", "category":"status", "target":"self", "priority":0, "accuracy":None, "power":None})["status"] == "unsupported"
    assert resolve_canonical_direct_heal_move(move={"move_id":"recover", "category":"status", "target":"self", "priority":0, "accuracy":100, "power":None})["status"] == "rejected"


def test_half_up_nominal_and_cap_are_path_local():
    snapshot, d0, actor, action = _inputs()
    authority = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor)
    result = materialize_detached_direct_heal(execution_authority=authority)
    assert result["status"] == "resolved"
    assert result["heal"] == {"pre_hp":101, "max_hp":301, "nominal_heal":151, "actual_heal":151, "post_hp":252}
    path = {"current_hp":250, "max_hp":301, "fainted":False}
    shifted = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, path_hp_authority=path)
    assert materialize_detached_direct_heal(execution_authority=shifted)["heal"] == {"pre_hp":250, "max_hp":301, "nominal_heal":151, "actual_heal":51, "post_hp":301}


def test_full_hp_and_fainted_are_not_fake_changes():
    snapshot, d0, actor, action = _inputs(301, 301)
    result = materialize_detached_direct_heal(execution_authority=freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor))
    assert result["outcome"] == "no_effect_full_hp" and result["heal"]["actual_heal"] == 0
    snapshot, d0, actor, action = _inputs(0, 301)
    assert materialize_detached_direct_heal(execution_authority=freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor))["status"] == "not_applicable"


def test_pair_uses_exact_order_and_ledger_replays_heal_fields():
    snapshot, d0, actor, own = _inputs(100, 301)
    target = d0["active_owners"]["opponent"]
    metadata = own["move_metadata_authority"]["metadata"]
    own_meta = {"status":"resolved", "move_id":"recover", "metadata":metadata, "candidate_id":own["action_id"], "active_attacker":actor, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"]}
    own = {**own, "move_metadata_authority":own_meta}
    opponent = {"status":"resolved", "action_id":"opponent_attack:recover", "action_type":"attack", "move_id":"recover", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "metadata_authority":{"status":"resolved", "move_id":"recover", "metadata":metadata}, "usability":{"status":"known_usable"}, "selectability":"selectable"}
    other = {"action_id":opponent["action_id"], "action_type":"attack", "identity":"recover", "metadata_authority":opponent["metadata_authority"]}
    left = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=own, actor=actor)
    right = freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=other, actor=target)
    order = {"status":"resolved", "schema_version":"runtime-d0-action-order-authority-v1", "order":"own_first", "order_engine":{"status":"own_faster"}, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "own_action_id":own["action_id"], "opponent_action_id":opponent["action_id"], "own_actor":actor, "opponent_actor":target}
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order, direct_heal_execution_authorities={own["action_id"]:left, opponent["action_id"]:right})
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator":1, "denominator":1}
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
