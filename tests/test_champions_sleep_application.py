from copy import deepcopy
import pytest

from llm.advisor_champions_sleep_application import (
    freeze_champions_direct_sleep_application as freeze_sleep,
    materialize_champions_direct_sleep_application as materialize_sleep,
    validate_champions_direct_sleep_application,
    materialize_champions_yawn_drowsiness as yawn,
    resolve_champions_yawn_at_end_of_turn as resolve_yawn,
    materialize_champions_rest as rest,
    validate_champions_rest,
)
from llm.advisor_champions_sleep_freeze_action_gate import freeze_champions_status_action_gate
from llm.advisor_reducer_state_model import project_atomic_transition, state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _complete_state, _owner, _snapshot, _state


def fixture(move="hypnosis", *, outcome="hit", **changes):
    state = _complete_state(_state())
    state["identity_groundedness_context"] = {"schema_version": "identity-groundedness-v1", "session_id": state["session_id"], "side": "opponent", "slot_index": 0, "pokemon_id": "opponent-a", "status": "grounded"}
    for key, value in changes.items():
        member = state["opponent_side"]["pokemon"][0] if key.startswith("target_") else state["self_side"]["pokemon"][0]
        field = key.removeprefix("target_").removeprefix("self_")
        member[field] = value
        if key.endswith("_condition"):
            member["condition_provenance"]["condition"] = value
        if key.endswith("_known_item"):
            member["known_item_provenance"]["status"] = "known"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = {"action_id": f"attack:{move}", "action_type": "attack", "identity": move}
    base = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "actor": actor, "target": target, "action_id": action["action_id"], "move_id": move}
    return snapshot, d0, actor, target, action, {"status": "resolved", **base, "outcome": outcome}


def refresh(snapshot, actor):
    snapshot = _snapshot(snapshot["state"]); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=actor)
    return snapshot, d0


def success(d0, actor, target, action, outcome="hit"):
    return {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "actor": actor, "target": target, "action_id": action["action_id"], "move_id": action["identity"], "outcome": outcome}


def test_hypnosis_establishes_the_existing_sleep_owner_and_gate_without_mutating_d0():
    snapshot, d0, actor, target, action, hit = fixture(); before = deepcopy((snapshot, d0)); authority = freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit); result = materialize_sleep(authority=authority, runtime_snapshot=snapshot)
    raw = result["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]
    assert authority["accuracy"] == 60 and result["sleep_applied"] and raw["champions_status_progression"]["sleep_duration"] is None and (snapshot, d0) == before
    next_d0 = freeze_runtime_strategy_d0(runtime_snapshot=result["runtime_snapshot"], decision_owner=target)
    gate = freeze_champions_status_action_gate(strategy_d0=next_d0, runtime_snapshot=result["runtime_snapshot"], actor=target, action_id="opponent_attack:tackle", move_id="tackle", action_order={})
    assert gate["status"] == "resolved" and {row["sleep_duration"] for row in gate["branches"]} == {2, 3}


@pytest.mark.parametrize("outcome,expected", [("missed", "move_missed"), ("blocked_by_protection", "blocked_by_protection")])
def test_direct_sleep_miss_and_protection_do_not_apply(outcome, expected):
    snapshot, d0, actor, target, action, hit = fixture(outcome=outcome); authority = freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)
    assert materialize_sleep(authority=authority, runtime_snapshot=snapshot)["outcome"] == expected


def test_direct_sleep_authority_tampering_is_rejected():
    snapshot, d0, actor, target, action, hit = fixture(); authority = freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit); authority["prevention"] = "move_missed"
    assert validate_champions_direct_sleep_application(authority)["status"] == "rejected" and materialize_sleep(authority=authority, runtime_snapshot=snapshot)["status"] == "rejected"


@pytest.mark.parametrize("condition", ["burn", "paralysis", "poison", "toxic", "freeze", "sleep"])
def test_existing_major_status_blocks_without_resetting_sleep(condition):
    snapshot, d0, actor, target, action, hit = fixture(target_condition=condition)
    authority = freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)
    assert authority["prevention"] == "target_already_major_statused"


@pytest.mark.parametrize("ability,expected", [("insomnia", "blocked_by_insomnia"), ("vital-spirit", "blocked_by_vital-spirit"), ("sweet-veil", "blocked_by_sweet-veil"), ("purifying-salt", "blocked_by_purifying-salt")])
def test_exact_sleep_immunity_blocks(ability, expected):
    snapshot, d0, actor, target, action, hit = fixture(target_current_ability=ability); authority = freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)
    assert authority["prevention"] == expected


def test_electric_terrain_requires_exact_groundedness():
    snapshot, d0, actor, target, action, hit = fixture(); snapshot["state"]["field"]["terrain"] = "electric"; snapshot, d0 = refresh(snapshot, actor); hit = success(d0, actor, target, action)
    assert freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["prevention"] == "blocked_by_electric_terrain"
    snapshot["state"]["identity_groundedness_context"]["status"] = "ungrounded"; snapshot, d0 = refresh(snapshot, actor); hit = success(d0, actor, target, action)
    assert isinstance(freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["prevention"], dict)
    snapshot["state"]["identity_groundedness_context"]["status"] = "unknown"; snapshot, d0 = refresh(snapshot, actor); hit = success(d0, actor, target, action)
    assert freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["status"] == "incomplete"


@pytest.mark.parametrize("move,accuracy", [("sleep-powder", 75), ("spore", 100)])
def test_powder_accuracy_and_immunities(move, accuracy):
    snapshot, d0, actor, target, action, hit = fixture(move); assert freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["accuracy"] == accuracy
    for field, value, expected in (("target_current_type", ["grass"], "blocked_by_grass_type"), ("target_current_ability", "overcoat", "blocked_by_overcoat"), ("target_known_item", "safety-goggles", "blocked_by_safety_goggles")):
        snapshot, d0, actor, target, action, hit = fixture(move, **{field: value}); assert freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["prevention"] == expected
    snapshot, d0, actor, target, action, hit = fixture(); assert isinstance(freeze_sleep(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit)["prevention"], dict)


def test_yawn_is_drowsy_then_resolves_only_at_next_boundary():
    snapshot, d0, actor, target, _, _ = fixture(); action = {"action_id": "attack:yawn", "action_type": "attack", "identity": "yawn"}; hit = success(d0, actor, target, action)
    established = yawn(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=hit, established_turn=4); assert established["drowsy_established"] and established["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=established["runtime_snapshot"], decision_owner=target)
    assert resolve_yawn(strategy_d0=d0, runtime_snapshot=established["runtime_snapshot"], target=target, resolution_turn=4)["reason"] == "yawn_resolution_boundary_invalid"
    resolved = resolve_yawn(strategy_d0=d0, runtime_snapshot=established["runtime_snapshot"], target=target, resolution_turn=5); assert resolved["sleep_applied"] and resolved["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["champions_status_progression"]["sleep_duration"] is None
    gate_d0 = freeze_runtime_strategy_d0(runtime_snapshot=resolved["runtime_snapshot"], decision_owner=target); assert freeze_champions_status_action_gate(strategy_d0=gate_d0, runtime_snapshot=resolved["runtime_snapshot"], actor=target, action_id="next", move_id="tackle", action_order={})["status"] == "resolved"


def test_yawn_switch_clears_and_later_safeguard_substitute_do_not_cancel_drowsiness():
    snapshot, d0, actor, target, _, _ = fixture(); action = {"action_id": "attack:yawn", "action_type": "attack", "identity": "yawn"}; established = yawn(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=success(d0, actor, target, action), established_turn=1)
    state = established["runtime_snapshot"]["state"]; state["opponent_side"]["side_conditions"] = ["safeguard"]; state["substitute_state_context"]["states"][1].update(state="known_active", substitute_hp=25); snap, d0 = refresh(established["runtime_snapshot"], target); assert resolve_yawn(strategy_d0=d0, runtime_snapshot=snap, target=target, resolution_turn=2)["sleep_applied"]
    state = established["runtime_snapshot"]["state"]; state["opponent_side"]["pokemon"][1] = deepcopy(state["opponent_side"]["pokemon"][0]); state["opponent_side"]["pokemon"][1]["pokemon_id"] = "bench"; event = {"observation_id": "switch", "observation_sequence": 2, "planned_effect": "switch_active", "trust": "user_confirmed_observation", "turn_number": 2, "side": "opponent", "switch_out_slot_index": 0, "switch_out_pokemon_id": "opponent-a", "switch_in_slot_index": 1, "switch_in_pokemon_id": "bench"}
    assert project_atomic_transition(state, {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [event]}, state["session_id"])["projected_state"]["opponent_side"]["pokemon"][0].get("champions_yawn_drowsiness") is None


def test_yawn_resolution_rechecks_major_condition_and_electric_terrain():
    snapshot, d0, actor, target, _, _ = fixture(); action = {"action_id": "attack:yawn", "action_type": "attack", "identity": "yawn"}; established = yawn(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=success(d0, actor, target, action), established_turn=1)
    state = established["runtime_snapshot"]["state"]; state["opponent_side"]["pokemon"][0]["condition"] = "burn"; state["opponent_side"]["pokemon"][0]["condition_provenance"]["condition"] = "burn"; snap, d0 = refresh(established["runtime_snapshot"], target); assert not resolve_yawn(strategy_d0=d0, runtime_snapshot=snap, target=target, resolution_turn=2)["sleep_applied"]
    snapshot, d0, actor, target, _, _ = fixture(); established = yawn(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, target=target, action=action, move_success_authority=success(d0, actor, target, action), established_turn=1); established["runtime_snapshot"]["state"]["field"]["terrain"] = "electric"; snap, d0 = refresh(established["runtime_snapshot"], target); assert resolve_yawn(strategy_d0=d0, runtime_snapshot=snap, target=target, resolution_turn=2)["outcome"] == "blocked_by_electric_terrain"


@pytest.mark.parametrize("condition", ["none", "burn", "poison", "paralysis"])
def test_rest_is_atomic_fixed_sleep_and_preserves_confusion(condition):
    snapshot, d0, actor, _, _, _ = fixture(); raw = snapshot["state"]["self_side"]["pokemon"][0]; raw["current_hp"] = 40; raw["condition"] = condition; raw["condition_provenance"]["condition"] = condition; raw["current_confusion"] = "confused"; action = {"action_id": "attack:rest", "action_type": "attack", "identity": "rest"}; snapshot, d0 = refresh(snapshot, actor)
    result = rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action); after = result["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]
    assert result["rest_applied"] and after["current_hp"] == after["max_hp"] and after["condition"] == "sleep" and after["current_confusion"] == "confused" and after["champions_status_progression"]["sleep_duration"] == 2
    gate_d0 = freeze_runtime_strategy_d0(runtime_snapshot=result["runtime_snapshot"], decision_owner=actor); gate = freeze_champions_status_action_gate(strategy_d0=gate_d0, runtime_snapshot=result["runtime_snapshot"], actor=actor, action_id="next", move_id="tackle", action_order={}); assert {row["sleep_duration"] for row in gate["branches"]} == {2}


def test_rest_failure_immunity_terrain_safeguard_and_early_bird():
    snapshot, d0, actor, _, _, _ = fixture(); raw = snapshot["state"]["self_side"]["pokemon"][0]; raw["current_hp"] = raw["max_hp"]; action = {"action_id": "attack:rest", "action_type": "attack", "identity": "rest"}; snapshot, d0 = refresh(snapshot, actor); assert rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action)["outcome"] == "rest_failed_full_hp"
    snapshot, d0, actor, _, _, _ = fixture(self_current_ability="insomnia"); snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 40; snapshot, d0 = refresh(snapshot, actor); assert not rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action)["rest_applied"]
    snapshot, d0, actor, _, _, _ = fixture(self_current_ability="early-bird"); snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 40; snapshot, d0 = refresh(snapshot, actor); result = rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action); gate_d0 = freeze_runtime_strategy_d0(runtime_snapshot=result["runtime_snapshot"], decision_owner=actor); gate = freeze_champions_status_action_gate(strategy_d0=gate_d0, runtime_snapshot=result["runtime_snapshot"], actor=actor, action_id="next", move_id="tackle", action_order={}); assert gate["branches"][0]["adjusted_duration"] == 1
    snapshot, d0, actor, _, _, _ = fixture(); snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 40; snapshot["state"]["self_side"]["side_conditions"] = ["safeguard"]; snapshot, d0 = refresh(snapshot, actor); assert rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action)["rest_applied"]
    snapshot, d0, actor, _, _, _ = fixture(); snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 40; snapshot["state"]["self_side"]["side_conditions"] = ["safeguard"]; snapshot["state"]["field"]["terrain"] = "electric"; snapshot["state"]["identity_groundedness_context"]["side"] = "self"; snapshot["state"]["identity_groundedness_context"]["pokemon_id"] = "self-a"; snapshot["state"]["identity_groundedness_context"]["status"] = "grounded"; snapshot, d0 = refresh(snapshot, actor); assert not rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action)["rest_applied"]


def test_rest_result_rejects_forged_partial_healing():
    snapshot, d0, actor, _, _, _ = fixture(); snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] = 40; action = {"action_id": "attack:rest", "action_type": "attack", "identity": "rest"}; snapshot, d0 = refresh(snapshot, actor); result = rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=actor, action=action); result["hp_after"] -= 1
    assert validate_champions_rest(result)["status"] == "rejected"
