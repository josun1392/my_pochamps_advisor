from copy import deepcopy

from llm.advisor_detached_current_healing_prevented_at_item_check_authority import materialize_detached_current_healing_prevented_at_item_check_authority
from llm.advisor_detached_intermediate_predictive_authority import freeze_detached_intermediate_predictive_authority
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_psychic_noise_healing_prevented_transition import attach_detached_psychic_noise_healing_prevented_transitions
from llm.advisor_detached_sitrus_berry_immediate_consumption import materialize_detached_sitrus_berry_immediate_consumption
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_intermediate_predictive_authority import _metadata_authority, _owner, _state
from tests.test_detached_opponent_response_profile import _inputs as _pair_inputs


MOVE = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}


def _inputs(*, hp=50, maximum=101, item="sitrus-berry", healing="inactive", move="tackle", damage=20):
    state = _state()
    target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=hp + damage, max_hp=maximum, known_item=item, healing_prevented_status=healing)
    target["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known", "source_observation_id": "item-1", "source_sequence": 1}
    target["healing_prevented_status_provenance"] = {"event_kind": "current_healing_prevented_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": healing, "source_observation_id": "hp-1", "source_sequence": 1}
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0]["current_ability"] = "pressure"
        state[f"{side}_side"]["pokemon"][0]["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "turn_number": 1, "source_observation_id": "magic-room-1", "source_sequence": 1}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    attacker, holder = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    bindings = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    leaf = {"leaf_id": "hit/0", "candidate_id": "attack:" + move, "action_type": "attack", "branch_path": ("hit",), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "consequences": {"damage": damage, "own_final_hp": 100, "target_final_hp": hp, "target_ko": hp == 0}, "provenance": {**bindings, "attacker": attacker, "target": holder, "move_id": move}}
    return state, snapshot, d0, attacker, holder, leaf


def _apply(**kwargs):
    state, snapshot, d0, attacker, holder, leaf = _inputs(**kwargs)
    result = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=leaf, holder=holder, move_metadata=MOVE)
    return state, snapshot, d0, attacker, holder, leaf, result


def test_exact_threshold_and_floor_recovery_are_applied_atomically():
    _state_value, snapshot, d0, _attacker, holder, leaf, result = _apply(hp=50, maximum=101)
    assert result["status"] == "resolved" and result["outcome"] == "activated"
    effect = result["sitrus_consequence"]
    assert effect["trigger_threshold"] == 50 and effect["heal_amount"] == 25 and effect["final_hp"] == 75
    assert result["leaf"]["consequences"]["target_final_hp"] == 75
    assert effect["item_after"] == {"status": "known_absent", "value": None, "consumption_cause": "sitrus_berry"}
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["known_item"] == "sitrus-berry"
    intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=result["leaf"])
    assert intermediate["active"]["opponent"]["hypothetical_hp"]["value"] == 75
    assert intermediate["active"]["opponent"]["hypothetical_item"]["source"] == "exact_terminal_leaf_sitrus_berry_consumption"
    authority = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=holder, target=d0["active_owners"]["self"], move_metadata_authority=_metadata_authority(d0))
    assert authority["status"] == "resolved"
    synthetic = authority["predictive_runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert synthetic["current_hp"] == 75 and synthetic["known_item"] is None


def test_below_threshold_activates_and_above_threshold_does_not():
    assert _apply(hp=49, maximum=101)[-1]["outcome"] == "activated"
    above = _apply(hp=51, maximum=101)[-1]
    assert above["status"] == "resolved" and above["outcome"] == "not_triggered"
    assert above["leaf"]["consequences"]["target_final_hp"] == 51


def test_ko_does_not_activate_and_maximum_clamps():
    ko = _apply(hp=0, maximum=101)[-1]
    assert ko["outcome"] == "not_triggered" and ko["leaf"]["consequences"]["target_final_hp"] == 0
    clamped = _apply(hp=100, maximum=101)[-1]
    assert clamped["outcome"] == "not_triggered"


def test_healing_prevented_and_same_hit_psychic_noise_suppress_without_consumption():
    present = _apply(hp=40, maximum=100, healing="active")[-1]
    assert present["outcome"] == "suppressed" and present["reason"] == "sitrus_healing_prevented"
    assert present["leaf"]["consequences"]["target_final_hp"] == 40
    state, snapshot, d0, attacker, holder, leaf = _inputs(hp=40, maximum=100, healing="inactive", move="psychic-noise")
    leaf["consequences"]["source_hit_context"] = {"target_routing": "target", "target_pre_hp": 60, "target_post_hp": 40, "actual_damage": 20}
    attached = attach_detached_psychic_noise_healing_prevented_transitions(strategy_d0=d0, runtime_snapshot=snapshot, ledger={"status": "evaluable", "terminal_leaves": (leaf,), "terminal_probability_mass": {"numerator": 1, "denominator": 1}})["terminal_leaves"][0]
    result = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=attached, holder=holder, move_metadata={**MOVE, "move_id": "psychic-noise"})
    assert result["status"] == "resolved" and result["outcome"] == "suppressed" and result["reason"] == "sitrus_healing_prevented"
    assert result["leaf"]["consequences"]["target_final_hp"] == 40
    intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=attached)
    projected = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=holder, target=attacker, move_metadata_authority=_metadata_authority(d0))
    assert projected["status"] == "resolved"
    path_local = projected["predictive_runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert path_local["healing_prevented_status"] == "active"


def test_unknown_healing_prevented_and_foreign_leaf_fail_closed():
    state, snapshot, d0, _attacker, holder, leaf = _inputs(hp=40, maximum=100)
    del d0["current_healing_prevented_authority"]
    unknown = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=leaf, holder=holder, move_metadata=MOVE)
    assert unknown["status"] in {"incomplete", "rejected"}
    _state_value, snapshot, d0, attacker, holder, leaf = _inputs(hp=40, maximum=100)
    leaf["provenance"]["target"] = attacker
    foreign = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=leaf, holder=holder, move_metadata=MOVE)
    assert foreign["status"] == "rejected"


def test_live_immediate_pair_projects_sitrus_to_pending_second_action():
    state, _old_snapshot, _old_d0, own, response_set, _orders = _pair_inputs(opponent_hp=60)
    target = state["opponent_side"]["pokemon"][0]
    target.update(current_hp=60, max_hp=100, known_item="sitrus-berry", healing_prevented_status="inactive")
    target["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known", "source_observation_id": "item-1", "source_sequence": 1}
    target["healing_prevented_status_provenance"] = {"event_kind": "current_healing_prevented_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "inactive", "source_observation_id": "hp-1", "source_sequence": 1}
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {"event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation", "turn_number": 1, "source_observation_id": "magic-room-1", "source_sequence": 1}
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); attacker, holder = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    own = deepcopy(own); opponent = deepcopy(next(row for row in response_set["actions"] if row["action_id"] == "opponent_attack:water-gun"))
    for action in (own, opponent):
        action.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]))
        meta = action.get("move_metadata_authority") or action.get("metadata_authority")
        meta.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]))
    own["move_metadata_authority"]["active_attacker"] = attacker
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "own_first", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own["action_id"], "opponent_action_id": opponent["action_id"], "own_actor": attacker, "opponent_actor": holder}
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order)
    assert pair["status"] == "evaluable", pair.get("reason")
    activated = [branch for branch in pair["terminal_branches"] if branch["first_action_leaf"]["consequences"].get("sitrus_berry_immediate_consumption", {}).get("outcome") == "activated"]
    assert activated
    branch = activated[0]
    effect = branch["first_action_leaf"]["consequences"]["sitrus_berry_immediate_consumption"]
    assert branch["intermediate_state_id"] is not None
    assert effect["final_hp"] == effect["post_hit_hp"] + 25


def test_magic_room_and_unsupported_multi_hit_fail_closed_without_consumption():
    state, snapshot, d0, _attacker, holder, leaf = _inputs(hp=40, maximum=100)
    snapshot["state"]["field"]["magic_room_status"] = "active"
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=d0["decision_owner"])
    holder = d0["active_owners"]["opponent"]
    leaf["provenance"].update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=d0["decision_owner"], target=holder)
    magic = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=leaf, holder=holder, move_metadata=MOVE)
    assert magic["status"] == "resolved" and magic["outcome"] == "suppressed" and magic["leaf"]["consequences"]["target_final_hp"] == 40
    _state_value, snapshot, d0, _attacker, holder, leaf = _inputs(hp=40, maximum=100)
    multi = materialize_detached_sitrus_berry_immediate_consumption(strategy_d0=d0, runtime_snapshot=snapshot, terminal_leaf=leaf, holder=holder, move_metadata={**MOVE, "min_hits": 2, "max_hits": 2})
    assert multi["status"] == "incomplete" and multi["leaf"]["consequences"]["target_final_hp"] == 40


def _second_action_sitrus_pair(*, healing="inactive", own_hp=100):
    state, _old_snapshot, _old_d0, own, _response_set, _orders = _pair_inputs(own_hp=own_hp, opponent_hp=60)
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        if healing is not None:
            pokemon["healing_prevented_status"] = healing
            pokemon["healing_prevented_status_provenance"] = {
                "event_kind": "current_healing_prevented_observed", "trust": "user_confirmed_observation",
                "turn_number": 1, "status": healing, "source_observation_id": f"{side}-healing", "source_sequence": 1,
            }
    holder = state["opponent_side"]["pokemon"][0]
    holder.update(known_item="sitrus-berry", max_hp=100)
    holder["known_item_provenance"] = {
        "event_kind": "current_item_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "status": "known", "source_observation_id": "opponent-sitrus", "source_sequence": 1,
    }
    state["field"]["magic_room_status"] = "inactive"
    state["field"]["magic_room_status_provenance"] = {
        "event_kind": "magic_room_field_observed", "trust": "user_confirmed_observation",
        "turn_number": 1, "source_observation_id": "magic-room", "source_sequence": 1,
    }
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own = deepcopy(own)
    own.update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]))
    own["move_metadata_authority"].update(session_id=d0["session_id"], source_runtime_fingerprint=d0["source_runtime_fingerprint"], source_branch_fingerprint=d0["strategy_preview_fingerprint"], decision_owner=deepcopy(d0["decision_owner"]), active_attacker=d0["active_owners"]["self"])
    opponent = {
        "status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": "opponent_attack:seismic-toss", "action_type": "attack", "identity": "seismic-toss", "move_id": "seismic-toss",
        "selectability": "selectable", "usability": {"status": "known_usable"},
        "opponent_actor": d0["active_owners"]["opponent"], "target_owner": d0["active_owners"]["self"],
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]),
        "metadata_authority": {"status": "resolved", "move_id": "seismic-toss", "metadata": {"move_id": "seismic-toss", "category": "physical", "type": "fighting", "accuracy": 100, "priority": 0}, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"])},
    }
    order = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": "opponent_first", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own["action_id"], "opponent_action_id": opponent["action_id"], "own_actor": d0["active_owners"]["self"], "opponent_actor": d0["active_owners"]["opponent"]}
    return materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=order)


def test_live_second_damaging_action_runs_sitrus_checkpoint_before_terminal_pair_certification():
    pair = _second_action_sitrus_pair()
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    second_leaves = [branch["second_action"]["leaf"] for branch in pair["terminal_branches"] if branch["second_action"]["state"] == "executed"]
    assert second_leaves and all("sitrus_berry_immediate_consumption" not in branch["first_action_leaf"]["consequences"] for branch in pair["terminal_branches"])
    effects = [leaf["consequences"]["sitrus_berry_immediate_consumption"] for leaf in second_leaves if "sitrus_berry_immediate_consumption" in leaf["consequences"]]
    assert effects
    assert all(effect["outcome"] == "activated" and effect["trigger_threshold"] == 50 and effect["heal_amount"] == 25 and effect["post_hit_hp"] <= 50 and effect["final_hp"] == effect["post_hit_hp"] + 25 for effect in effects)
    assert all(effect["item_after"] == {"status": "known_absent", "value": None, "consumption_cause": "sitrus_berry"} for effect in effects)
    ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)
    assert ledger["status"] == "evaluable"
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger=ledger)["status"] == "resolved"


def test_second_action_sitrus_suppression_and_cancellation_do_not_consume_it():
    suppressed = _second_action_sitrus_pair(healing="active")
    assert suppressed["status"] == "evaluable"
    hit_leaves = [branch["second_action"]["leaf"] for branch in suppressed["terminal_branches"] if branch["second_action"]["leaf"]["hit_state"] == "hit"]
    assert hit_leaves and all("sitrus_berry_immediate_consumption" not in leaf["consequences"] for leaf in hit_leaves)
    cancelled = _second_action_sitrus_pair(own_hp=50)
    assert cancelled["status"] == "evaluable"
    assert all(branch["second_action"]["state"] == "cancelled_due_to_faint" for branch in cancelled["terminal_branches"])


def test_second_action_sitrus_unknown_path_local_healing_authority_fails_closed():
    result = _second_action_sitrus_pair(healing=None)
    assert result["status"] in {"incomplete", "rejected"}
