from copy import deepcopy

from advisor.canonical_atomic_item_swap_status import resolve_atomic_item_swap_side_legality
from llm.advisor_detached_atomic_item_swap_status_materializer import materialize_detached_atomic_item_swap_status
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_runtime_d0_atomic_item_swap_status_execution_authority import freeze_runtime_d0_atomic_item_swap_status_execution_authority
from llm.advisor_reducer_state_model import make_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _inputs(actor_item="choice-scarf", target_item="black-belt", actor_ability="pressure", target_ability="pressure"):
    state = _state()
    for side, item, ability in (("self", actor_item, actor_ability), ("opponent", target_item, target_ability)):
        row = state[f"{side}_side"]["pokemon"][0]
        row["known_item"], row["current_ability"] = item, ability
        row["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known" if item else "known_absent"}
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    metadata = {"move_id": "trick", "category": "status", "target": "selected-pokemon"}
    action = {"action_id": "attack:trick", "action_type": "attack", "identity": "trick", "move_metadata_authority": {"status": "resolved", "metadata": metadata}}
    app = {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "actor": actor, "target": target, "action_id": action["action_id"], "move_id": "trick", "outcome": "ordinary"}
    return state, snapshot, d0, action, actor, target, app


def _authority(**changes):
    state, snapshot, d0, action, actor, target, app = _inputs(**changes)
    return state, d0, freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, execution_applicability_authority=app)


def test_atomic_swap_and_one_sided_outcomes_are_exact_and_detached():
    state, _, authority = _authority()
    assert authority["outcome"] == "executed_swap"
    assert authority["actor_item_before"] == {"state": "known_present", "item": "choice-scarf"}
    assert authority["actor_item_after"] == {"state": "known_present", "item": "black-belt"}
    leaf = materialize_detached_atomic_item_swap_status(execution_authority=authority)
    assert leaf["status"] == "resolved" and leaf["item_transition"]["target_item_after"] == {"state": "known_present", "item": "choice-scarf"}
    assert authority["transition_kind"] == "swap_two_items"
    assert state["self_side"]["pokemon"][0]["known_item"] == "choice-scarf"
    for actor_item, target_item, after_actor, after_target in (("choice-scarf", None, None, "choice-scarf"), (None, "black-belt", "black-belt", None)):
        _, _, one = _authority(actor_item=actor_item, target_item=target_item)
        one_leaf = materialize_detached_atomic_item_swap_status(execution_authority=one)
        assert one["outcome"] == "executed_swap"
        assert one_leaf["item_transition"]["actor_item_after"]["item"] == after_actor
        assert one_leaf["item_transition"]["target_item_after"]["item"] == after_target


def test_unknown_restriction_sticky_hold_and_forgery_fail_closed():
    _, _, both_absent = _authority(actor_item=None, target_item=None)
    assert both_absent["outcome"] == "failed_both_no_item"
    _, _, sticky = _authority(target_ability="sticky-hold")
    assert sticky["outcome"] == "blocked_sticky_hold" and sticky["actor_item_after"] == sticky["actor_item_before"]
    _, _, gas = _authority(target_ability="sticky-hold", actor_ability="neutralizing-gas")
    assert gas["outcome"] == "executed_swap" and gas["ability_authority"]["sticky_hold_active"] is False
    state, _, _, action, _, _, _ = _inputs()
    state["self_side"]["pokemon"][0]["known_item"] = make_unknown_battle_fact(); state["self_side"]["pokemon"][0]["known_item_provenance"] = None; snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    app = {"status":"resolved", "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "actor":actor, "target":target, "action_id":action["action_id"], "move_id":"trick", "outcome":"ordinary"}
    unknown = freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, execution_applicability_authority=app)
    assert unknown["status"] == "incomplete" and unknown["outcome"] == "incomplete_authority"
    _, _, authority = _authority()
    forged = deepcopy(authority); forged["actor_item_after"] = forged["actor_item_before"]
    assert materialize_detached_atomic_item_swap_status(execution_authority=forged)["status"] == "rejected"
    _, _, blocked = _authority()
    state, snapshot, d0, action, actor, target, app = _inputs(); app["outcome"] = "prevented"
    protection = freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, execution_applicability_authority=app)
    assert protection["outcome"] == "blocked_protection"


def test_special_item_legality_and_identity_bindings_fail_closed():
    special = resolve_atomic_item_swap_side_legality(holder_item_authority={"status":"known", "value":"abomasite"}, holder_species="abomasnow", incoming_item_authority={"status":"known_absent"})
    assert special["status"] == "resolved" and special["transferable"] is False
    _, snapshot, d0, action, actor, target, app = _inputs()
    forged_action = deepcopy(action); forged_action["identity"] = "switcheroo"
    assert freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=forged_action, actor=actor, target=target, execution_applicability_authority=app)["status"] == "rejected"
    foreign = deepcopy(app); foreign["target"] = actor
    assert freeze_runtime_d0_atomic_item_swap_status_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action, actor=actor, target=target, execution_applicability_authority=foreign)["status"] == "rejected"


def test_detached_intermediate_state_exposes_both_swap_items():
    state, d0, authority = _authority()
    swap = materialize_detached_atomic_item_swap_status(execution_authority=authority)
    leaf = {"action_type": "attack", "candidate_id": "attack:trick", "leaf_id": "swap", "branch_path": (), "probability": {"numerator": 1, "denominator": 1}, "damage_roll": "not_applicable", "hit_state": "not_applicable", "critical_state": "not_applicable", "provenance": {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "attacker": d0["active_owners"]["self"], "target": d0["active_owners"]["opponent"], "move_id": "trick"}, "consequences": {"own_final_hp": 100, "target_final_hp": 100, **swap["consequences"]}}
    intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    assert intermediate["status"] == "resolved"
    assert intermediate["active"]["self"]["hypothetical_item"]["value"] == "black-belt"
    assert intermediate["active"]["opponent"]["hypothetical_item"]["value"] == "choice-scarf"
    assert state["self_side"]["pokemon"][0]["known_item"] == "choice-scarf"
