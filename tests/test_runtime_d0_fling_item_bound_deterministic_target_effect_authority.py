from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from advisor.canonical_fling_item_metadata import resolve_canonical_fling_item_metadata
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_item_execution_authority import freeze_runtime_d0_fling_item_execution_authority
from llm.advisor_runtime_d0_fling_item_bound_deterministic_target_effect_authority import (
    freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority,
    materialize_detached_fling_item_bound_deterministic_target_effect,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _inputs


def _inputs_for(item: str, *, target_type=("normal",), target_condition="none"):
    state, snapshot, d0, _own, _responses, _orders = _inputs()
    own, foe = state["self_side"]["pokemon"][0], state["opponent_side"]["pokemon"][0]
    own["known_item"] = item; own["known_item_provenance"]["status"] = "known"
    foe["current_type"] = list(target_type); foe["condition"] = target_condition
    foe["condition_provenance"]["condition"] = target_condition
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "source_observation_id": "mr", "source_sequence": 1}
    snapshot = {**snapshot, "state": state, "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["active_owners"]["self"])
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    action = {"action_id": "attack:fling", "action_type": "attack", "identity": "fling", "move_metadata_authority": {"status": "resolved", "metadata": resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]}}
    execution = freeze_runtime_d0_fling_item_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target)
    # This prerequisite consumes the prospective post-throw boundary; Core v1
    # intentionally still rejects mandatory effects until its next consumer task.
    record = resolve_canonical_fling_item_metadata(item)
    execution = {**execution, "status": "resolved", "outcome": "ready_throw", "item_after": {"state": "known_absent", "item": None}, "fling_item_metadata": record}
    leaf = {"leaf_id": "hit/non_critical/damage_roll:0", "candidate_id": "attack:fling", "hit_state": "hit", "provenance": {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "attacker": actor, "target": target, "move_id": "fling", "fling_execution_authority": execution}, "consequences": {"source_hit_context": {"source_action_id": "attack:fling", "source_move_id": "fling", "actual_damage": 30, "target_routing": "target"}, "target_final_hp": 70, "target_ko": False}}
    return d0, snapshot, execution, leaf


def test_inventory_has_exact_deterministic_non_berry_subset() -> None:
    records = [resolve_canonical_fling_item_metadata(item) for item in ("light-ball", "poison-barb", "kings-rock", "oran-berry")]
    assert [(row["item_id"], row["effect"]["kind"]) for row in records] == [("light-ball", "major_status"), ("poison-barb", "major_status"), ("kings-rock", "flinch"), ("oran-berry", "berry_effect")]


def test_light_ball_binds_item_leaf_and_applies_paralysis_without_mutation() -> None:
    d0, snapshot, execution, leaf = _inputs_for("light-ball")
    before = deepcopy(snapshot)
    result = freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf)
    assert result["status"] == "resolved" and result["outcome"] == "applied_major_status"
    detached = materialize_detached_fling_item_bound_deterministic_target_effect(authority=result)
    assert detached["hypothetical_target_condition"]["resulting_condition"] == "paralysis"
    assert snapshot == before


def test_poison_barb_status_boundaries_fail_closed_or_preserve_existing_status() -> None:
    d0, snapshot, execution, leaf = _inputs_for("poison-barb", target_type=("steel",))
    prevented = freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf)
    assert prevented["outcome"] == "prevented"
    d0, snapshot, execution, leaf = _inputs_for("poison-barb", target_condition="burn")
    existing = freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf)
    assert existing["outcome"] == "no_transition_already_statused"
    miss = deepcopy(leaf); miss["hit_state"] = "miss"
    assert freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=miss)["outcome"] == "not_applicable"


def test_kings_rock_flinch_requires_exact_pending_action_and_retains_fling_provenance() -> None:
    d0, snapshot, execution, leaf = _inputs_for("kings-rock")
    target = d0["active_owners"]["opponent"]
    pending = {"action_id": "opponent_attack:water-gun", "action_type": "attack", "actor": target}
    result = freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf, pending_target_action=pending, action_order="own_first")
    assert result["outcome"] == "applied_flinch_pending_action"
    marker = materialize_detached_fling_item_bound_deterministic_target_effect(authority=result)["hypothetical_target_flinch"]
    assert marker["source_fling_item"] == "kings-rock" and marker["provenance"] == "fling_item_bound_deterministic_flinch_v1"
    assert freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf, pending_target_action={**pending, "actor": d0["active_owners"]["self"]}, action_order="own_first")["status"] == "rejected"


def test_wrong_item_forged_leaf_and_berry_are_rejected_or_unsupported() -> None:
    d0, snapshot, execution, leaf = _inputs_for("light-ball")
    forged = deepcopy(leaf); forged["provenance"]["fling_execution_authority"]["user_item_before"]["value"] = "poison-barb"
    assert freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=forged)["status"] == "rejected"
    d0, snapshot, execution, leaf = _inputs_for("oran-berry")
    assert freeze_runtime_d0_fling_item_bound_deterministic_target_effect_authority(strategy_d0=d0, runtime_snapshot=snapshot, fling_execution_authority=execution, source_leaf=leaf)["status"] == "unsupported"
