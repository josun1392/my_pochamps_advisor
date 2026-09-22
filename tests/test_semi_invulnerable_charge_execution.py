from copy import deepcopy
from fractions import Fraction

import pytest

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_semi_invulnerable_charge_authority import (
    freeze_detached_semi_invulnerable_targetability_authority,
    materialize_detached_semi_invulnerable_charge_state_authority,
    materialize_semi_invulnerable_exception_damage_modifier_authority,
    materialize_semi_invulnerable_state_retirement,
    validate_detached_semi_invulnerable_charge_state_authority,
)
from llm.advisor_detached_standard_charge_start import materialize_detached_standard_charge_start
from llm.advisor_detached_next_turn_action_intent import materialize_detached_next_turn_action_intents
from llm.advisor_detached_next_turn_action_order_authority import materialize_detached_next_turn_action_order_authority
from llm.advisor_detached_next_turn_ordinary_attack_execution import (
    execute_detached_next_turn_ordinary_attack,
    materialize_detached_next_turn_ordinary_attack_execution_authority,
)
from llm.advisor_detached_next_turn_pair_local_predictive_mechanics import materialize_detached_next_turn_pair_local_predictive_mechanics
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_lifecycle_confirmation import GRAVITY_SOURCE, LOCKED_ON_SOURCE
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import (
    freeze_runtime_d0_standard_charge_start_readiness_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_sandstorm_residual_core import evaluate_sandstorm_residual
from llm.advisor_standard_charge_terminal_execution import (
    execute_standard_charge_terminal_attack,
    materialize_standard_charge_terminal_execution_contract,
)
from llm.advisor_reducer_state_model import state_fingerprint
from tests.test_detached_opponent_response_profile import _complete_state, _metadata, _owner, _snapshot, _state
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from tests.test_standard_charge_start_immediate_pair_integration import (
    _opponent_action,
    _order,
    _own_action,
    _with_terminal_mechanics_facts,
)

SEMI = ("fly", "dig", "dive", "bounce")
CLASS = {"fly": "airborne", "bounce": "airborne", "dig": "underground", "dive": "underwater"}


def _semi_metadata(move_id):
    effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert effect["status"] == "resolved"
    return {**deepcopy(effect["move"]), "priority": 0, "target": "selected-pokemon"}


def _exact_current_facts(state, *, gravity="inactive", opponent_locked="inactive", no_guard_side=None):
    state["field"]["gravity_status"] = gravity
    state["field"]["gravity_status_provenance"] = {
        "event_kind": "gravity_field_observed",
        "trust": "user_confirmed_observation",
        "source": GRAVITY_SOURCE,
        "turn_number": 1,
        "source_observation_id": "gravity:1",
        "source_sequence": 1,
    }
    for side in ("self", "opponent"):
        raw = state[f"{side}_side"]["pokemon"][0]
        raw["current_ability"] = "no-guard" if side == no_guard_side else "pressure"
        raw["current_ability_provenance"] = {
            "event_kind": "current_ability_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
        }
    raw = state["opponent_side"]["pokemon"][0]
    if opponent_locked == "inactive":
        raw["locked_on_state"] = {"status": "known_inactive"}
    elif opponent_locked == "active":
        raw["locked_on_state"] = {"status": "known_active", "bound_target": _owner(state, "self")}
    elif opponent_locked == "wrong":
        raw["locked_on_state"] = {"status": "known_active", "bound_target": _owner(state, "opponent")}
    else:
        raw["locked_on_state"] = {"knowledge": "unknown"}
        raw.pop("locked_on_state_provenance", None)
        return state
    raw["locked_on_state_provenance"] = {
        "event_kind": "current_locked_on_state_observed",
        "trust": "user_confirmed_observation",
        "source": LOCKED_ON_SOURCE,
        "turn_number": 1,
        "source_observation_id": "locked:1",
        "source_sequence": 2,
    }
    return state


def _case(move_id="fly", *, gravity="inactive", power_herb=False, opponent_locked="inactive", no_guard_side=None, hp=100, condition="none"):
    state = _with_terminal_mechanics_facts(_complete_state(_state()))
    state["self_side"]["pokemon"][0]["current_hp"] = hp
    state["self_side"]["pokemon"][0]["max_hp"] = 100
    state["self_side"]["pokemon"][0]["fainted"] = hp == 0
    state["self_side"]["pokemon"][0]["condition"] = condition
    state["self_side"]["pokemon"][0]["condition_provenance"] = {"event_kind":"current_condition_observed","trust":"user_confirmed_observation","condition":condition,"turn_number":1}
    _exact_current_facts(state, gravity=gravity, opponent_locked=opponent_locked, no_guard_side=no_guard_side)
    if power_herb:
        raw = state["self_side"]["pokemon"][0]
        raw["known_item"] = "power-herb"
        raw["known_item_provenance"] = {
            "event_kind": "current_item_observed",
            "trust": "user_confirmed_observation",
            "turn_number": 1,
            "status": "known",
        }
        state["field"]["magic_room_status"] = "inactive"
        state["field"]["magic_room_status_provenance"] = {
            "event_kind": "magic_room_field_observed",
            "trust": "user_confirmed_observation",
            "source_observation_id": "magic:1",
            "source_sequence": 3,
        }
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, move_id, metadata=_semi_metadata(move_id))
    return state, snapshot, d0, actor, target, action


@pytest.mark.parametrize(("move_id","power","type_","accuracy","cls"), [
    ("fly",90,"flying",95,"airborne"),
    ("dig",80,"ground",100,"underground"),
    ("dive",80,"water",100,"underwater"),
    ("bounce",85,"flying",85,"airborne"),
])
def test_canonical_terminal_inventory_and_charge_state(move_id,power,type_,accuracy,cls):
    _state0,snapshot,d0,actor,target,action=_case(move_id)
    effect=resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert (effect["move"]["power"],effect["move"]["type"],effect["move"]["category"],effect["move"]["accuracy"])==(power,type_,"physical",accuracy)
    if move_id=="bounce":
        assert effect["secondary"]=={"kind":"status","chance":30,"condition":"paralysis"}
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert readiness["outcome"]=="charge_start_ready", readiness
    start=materialize_detached_standard_charge_start(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,readiness_authority=readiness)
    assert start["status"]=="resolved", (start.get("status"), start.get("reason"))
    semi=start["semi_invulnerable_charge_state_authority"]
    assert semi["state"]=="active" and semi["semi_invulnerability_class"]==cls
    assert semi["owner"]==actor and semi["original_target"]==target
    assert semi["source_action_id"]==action["action_id"] and semi["source_move_id"]==move_id
    assert semi["hypothetical"] is True and semi["observation_emitted"] is False
    assert start["action_leaf"]["consequences"]["semi_invulnerable_charge_state"]==semi
    intermediate=materialize_detached_predictive_intermediate_state(strategy_d0=d0,terminal_leaf=start["action_leaf"])
    assert intermediate["status"]=="resolved", intermediate
    assert intermediate["semi_invulnerable_charge_state_authority"]==semi


@pytest.mark.parametrize("move_id",("fly","bounce"))
def test_active_gravity_blocks_airborne_start_and_unknown_fails_closed(move_id):
    _s,snapshot,d0,actor,target,action=_case(move_id,gravity="active")
    blocked=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert blocked["status"]=="unsupported" and blocked["reason"]=="semi_invulnerable_charge_blocked_by_active_gravity"
    state,snapshot,d0,actor,target,action=_case(move_id)
    state["field"]["gravity_status"]={"knowledge":"unknown"}; state["field"].pop("gravity_status_provenance",None)
    snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":deepcopy(state),"state_fingerprint":state_fingerprint(state)}
    d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=actor)
    action=_own_action(d0,actor,move_id,metadata=_semi_metadata(move_id))
    unknown=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert unknown["status"]=="incomplete" and unknown["reason"]=="current_gravity_state_unknown"


@pytest.mark.parametrize("move_id",("fly","bounce"))
def test_power_herb_does_not_bypass_active_gravity_start_restriction(move_id):
    _s,snapshot,d0,actor,target,action=_case(move_id,gravity="active",power_herb=True)
    result=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert result["status"]=="unsupported"
    assert result["reason"]=="semi_invulnerable_charge_blocked_by_active_gravity"


@pytest.mark.parametrize("move_id",("dig","dive"))
def test_dig_dive_start_do_not_depend_on_gravity(move_id):
    _s,snapshot,d0,actor,target,action=_case(move_id,gravity="active")
    result=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert result["status"]=="resolved" and result["outcome"]=="charge_start_ready"


def _state_authority(move_id="fly"):
    _s,snapshot,d0,actor,target,action=_case(move_id)
    return snapshot,d0,actor,target,action,materialize_detached_semi_invulnerable_charge_state_authority(
        strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,target=target,action_id=action["action_id"],move_id=move_id,source_leaf_id=f"{action['action_id']}:charge-start",
    )


def _incoming(d0, move_id, metadata):
    row=_opponent_action(d0,move_id,metadata=metadata)
    return row,row["metadata_authority"]


@pytest.mark.parametrize(("move_id","incoming","multiplier"),[
    ("fly","gust",2),("fly","twister",2),("fly","sky-uppercut",1),("fly","thunder",1),("fly","hurricane",1),("fly","smack-down",1),("fly","thousand-arrows",1),
    ("dig","earthquake",2),("dig","magnitude",2),("dive","surf",2),("dive","whirlpool",2),
])
def test_exact_exception_matrix_and_modifier(move_id,incoming,multiplier):
    snapshot,d0,_actor,_original_target,_action,state=_state_authority(move_id)
    target=state["owner"]
    metadata={"move_id":incoming,"category":"special" if incoming in {"gust","twister","thunder","surf"} else "physical","power":80,"type":"normal","accuracy":100,"priority":0}
    action,meta=_incoming(d0,incoming,metadata)
    attacker=d0["active_owners"]["opponent"]
    auth=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=action,incoming_move_metadata_authority=meta,attacker=attacker,target=target,semi_invulnerable_state_authority=state)
    assert auth["status"]=="resolved" and auth["outcome"]=="allowed_by_exact_exception", (auth.get("status"), auth.get("reason"))
    assert auth["exception_multiplier"]==multiplier
    modifier=materialize_semi_invulnerable_exception_damage_modifier_authority(auth)
    assert modifier["modifier_q12"]==4096*multiplier
    forged=deepcopy(modifier); forged["incoming_move_id"]="forged"
    assert forged != materialize_semi_invulnerable_exception_damage_modifier_authority(auth)


def test_unknown_incoming_metadata_and_unknown_locked_on_fail_closed():
    snapshot,d0,_actor,_target,_action,state=_state_authority("fly")
    target=state["owner"]; attacker=d0["active_owners"]["opponent"]
    bad_action={"action_id":"opponent_attack:unknown","action_type":"attack","move_id":"tackle"}
    incomplete=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=bad_action,incoming_move_metadata_authority={"status":"incomplete"},attacker=attacker,target=target,semi_invulnerable_state_authority=state)
    assert incomplete["status"]=="incomplete"

    _s,snapshot,d0,actor,original_target,action=_case("fly",opponent_locked="unknown")
    state=materialize_detached_semi_invulnerable_charge_state_authority(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,target=original_target,action_id=action["action_id"],move_id="fly",source_leaf_id="attack:fly:charge-start")
    tackle,meta=_incoming(d0,"tackle",_metadata("tackle")["metadata"])
    result=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=tackle,incoming_move_metadata_authority=meta,attacker=d0["active_owners"]["opponent"],target=state["owner"],semi_invulnerable_state_authority=state)
    assert result["status"]=="incomplete" and result["reason"]=="current_locked_on_state_unknown"


def test_locked_on_no_guard_and_blocked_targetability():
    snapshot,d0,_actor,_original_target,_action,state=_state_authority("fly")
    target=state["owner"]
    tackle,meta=_incoming(d0,"tackle",_metadata("tackle")["metadata"])
    attacker=d0["active_owners"]["opponent"]
    blocked=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=tackle,incoming_move_metadata_authority=meta,attacker=attacker,target=target,semi_invulnerable_state_authority=state)
    assert blocked["status"]=="resolved" and blocked["outcome"]=="blocked_by_semi_invulnerability", (blocked.get("status"), blocked.get("reason"))

    _s,snapshot,d0,actor,target,action=_case("fly",opponent_locked="active")
    state=materialize_detached_semi_invulnerable_charge_state_authority(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,target=target,action_id=action["action_id"],move_id="fly",source_leaf_id="attack:fly:charge-start")
    semi_target=state["owner"]
    tackle,meta=_incoming(d0,"tackle",_metadata("tackle")["metadata"])
    locked=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=tackle,incoming_move_metadata_authority=meta,attacker=d0["active_owners"]["opponent"],target=semi_target,semi_invulnerable_state_authority=state)
    assert locked["outcome"]=="allowed_by_locked_on" and locked["accuracy_bypassed"] is True

    _s,snapshot,d0,actor,target,action=_case("fly",opponent_locked="inactive",no_guard_side="opponent")
    state=materialize_detached_semi_invulnerable_charge_state_authority(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,target=target,action_id=action["action_id"],move_id="fly",source_leaf_id="attack:fly:charge-start")
    semi_target=state["owner"]
    tackle,meta=_incoming(d0,"tackle",_metadata("tackle")["metadata"])
    noguard=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=tackle,incoming_move_metadata_authority=meta,attacker=d0["active_owners"]["opponent"],target=semi_target,semi_invulnerable_state_authority=state)
    assert noguard["outcome"]=="allowed_by_no_guard" and noguard["accuracy_bypassed"] is True

    _s,snapshot,d0,actor,target,action=_case("fly",opponent_locked="wrong")
    state=materialize_detached_semi_invulnerable_charge_state_authority(strategy_d0=d0,runtime_snapshot=snapshot,actor=actor,target=target,action_id=action["action_id"],move_id="fly",source_leaf_id="attack:fly:charge-start")
    tackle,meta=_incoming(d0,"tackle",_metadata("tackle")["metadata"])
    wrong=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=tackle,incoming_move_metadata_authority=meta,attacker=d0["active_owners"]["opponent"],target=state["owner"],semi_invulnerable_state_authority=state)
    assert wrong.get("outcome") not in {"allowed_by_locked_on","allowed_by_no_guard","allowed_by_exact_exception"}


@pytest.mark.parametrize("move_id",SEMI)
def test_power_herb_executes_same_turn_without_waiting_state(move_id):
    _s,snapshot,d0,actor,target,action=_case(move_id,power_herb=True)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert readiness["outcome"]=="power_herb_charge_skip_ready", readiness
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":move_id},readiness_authority=readiness)
    assert authority["status"]=="resolved", authority
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved", kernel
    assert kernel["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    assert all("semi_invulnerable_charge_state" not in leaf["consequences"] for leaf in kernel["terminal_leaves"])
    executing=[leaf for leaf in kernel["terminal_leaves"] if "power_herb_consumption" in leaf["consequences"]]
    assert executing


def test_fly_power_herb_miss_consumes_and_pre_action_cancel_does_not():
    _s,snapshot,d0,actor,target,action=_case("fly",power_herb=True)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"fly"},readiness_authority=readiness)
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    misses=[leaf for leaf in kernel["terminal_leaves"] if leaf["hit_state"]=="miss"]
    assert misses and all("power_herb_consumption" in leaf["consequences"] for leaf in misses)
    assert all("semi_invulnerable_charge_state" not in leaf["consequences"] for leaf in misses)

    _s,snapshot,d0,actor,target,action=_case("fly",power_herb=True,condition="paralysis")
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert readiness["outcome"]=="power_herb_charge_skip_ready", readiness
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"fly"},readiness_authority=readiness)
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved"
    cancelled=[leaf for leaf in kernel["terminal_leaves"] if "cancelled_due_to_paralysis" in leaf["branch_path"]]
    assert cancelled
    assert all("power_herb_consumption" not in leaf["consequences"] and "semi_invulnerable_charge_state" not in leaf["consequences"] for leaf in cancelled)


@pytest.mark.parametrize("move_id",("dig","dive"))
def test_full_eot_sandstorm_path_preserves_hp_while_state_active(move_id):
    handoff=_production_temporal_handoff(own_move=move_id,opponent_move="razor-wind",weather="sandstorm")
    active=handoff["next_state"]["active"]["self"]
    assert active["current_hp"]==100
    row=handoff["next_state"]["next_turn_standard_charge_continuation_authorities"]["self"]
    assert row["semi_invulnerable_charge_state_authority"]["state"]=="active"


def test_sandstorm_immunity_is_only_underground_or_underwater_active_state():
    abilities={"self":"pressure","opponent":"pressure"}
    for move_id in ("dig","dive"):
        _snapshot0,_d0,_actor,_target,_action,state=_state_authority(move_id)
        result=evaluate_sandstorm_residual(current_type=["normal"],item=None,active_abilities=abilities,target_side="self",current_hp=100,maximum_hp=100,semi_invulnerable_state=state)
        assert result["status"]=="complete" and result["residual_damage"]==0 and result["outcome"]=="immune_while_semi_invulnerable"
    _snapshot0,_d0,_actor,_target,_action,fly=_state_authority("fly")
    wrong=evaluate_sandstorm_residual(current_type=["normal"],item=None,active_abilities=abilities,target_side="self",current_hp=100,maximum_hp=100,semi_invulnerable_state=fly)
    assert wrong["status"]=="incomplete"
    normal=evaluate_sandstorm_residual(current_type=["normal"],item=None,active_abilities=abilities,target_side="self",current_hp=100,maximum_hp=100)
    assert normal["residual_damage"]==6


@pytest.mark.parametrize("move_id",SEMI)
def test_state_tamper_and_generic_guard(move_id):
    snapshot,d0,actor,target,action,state=_state_authority(move_id)
    forged=deepcopy(state); forged["semi_invulnerability_class"]="vanished"
    assert validate_detached_semi_invulnerable_charge_state_authority(forged) is not None
    forged_action=deepcopy(state); forged_action["source_action_id"]="forged"
    assert validate_detached_semi_invulnerable_charge_state_authority(forged_action) is not None
    forged_move=deepcopy(state); forged_move["source_move_id"]="phantom-force"
    assert validate_detached_semi_invulnerable_charge_state_authority(forged_move) is not None
    retirement=materialize_semi_invulnerable_state_retirement(active_state_authority=state,source_leaf_id="terminal:1",reason="terminal_attack_executed")
    assert retirement["status"]=="resolved" and retirement["state_after"]=="inactive"
    retired_forged=deepcopy(retirement); retired_forged["state_after"]="active"
    assert retired_forged != materialize_semi_invulnerable_state_retirement(active_state_authority=state,source_leaf_id="terminal:1",reason="terminal_attack_executed")
    from core.charge_move_repository import ChargeMoveRepository
    guard=ChargeMoveRepository().immediate_execution_guard(move_id)
    assert guard["reason"]=="two_turn_execution_unrepresented" and guard["canonical_recognition_grants_immediate_execution"] is False


@pytest.mark.parametrize("move_id", SEMI)
def test_eot_next_turn_transport_forced_continuation_and_retirement(move_id):
    handoff = _production_temporal_handoff(own_move=move_id, opponent_move="razor-wind")
    state = handoff["next_state"]
    fingerprint = handoff["resulting_branch_fingerprint"]
    row = state["next_turn_standard_charge_continuation_authorities"]["self"]
    assert row["status"] == "known_present"
    semi = row["semi_invulnerable_charge_state_authority"]
    assert semi["state"] == "active" and semi["source_move_id"] == move_id

    forced = materialize_detached_standard_charge_forced_continuation(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
    )
    assert forced["status"] == "resolved", forced
    forced_self = forced["forced_continuation_actions"]["self"]
    assert forced_self["status"] == "resolved"
    assert forced_self["semi_invulnerable_charge_state_authority"] == semi

    authority = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state,
        next_decision_fingerprint=fingerprint,
        forced_continuation=forced,
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
    )
    assert authority["status"] == "resolved", authority
    assert authority["actions"]["self"]["semi_invulnerable_charge_state_authority"] == semi

    contract = materialize_detached_standard_charge_turn_two_terminal_execution_contract(
        execution_authority=authority, side="self",
    )
    assert contract["status"] == "resolved", contract
    assert contract["semi_invulnerable_charge_state_authority"] == semi

    result = execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    assert result["status"] == "resolved", result
    ledger = result["actions"]["self"]
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert ledger["terminal_leaves"]
    assert all(
        leaf["consequences"]["semi_invulnerable_state_retirement"]["state_after"] == "inactive"
        for leaf in ledger["terminal_leaves"]
    )


def test_bounce_secondary_catalog_is_exact_thirty_percent():
    from advisor.probabilistic_target_status_effect_capabilities import (
        resolve_probabilistic_target_status_effect_capability,
    )
    move = resolve_canonical_standard_charge_turn_two_effect("bounce")["move"]
    source = {
        "target_condition": {"status": "known_none"},
        "target_types": {"status": "known", "values": ("normal",)},
        "attacker_ability": {"status": "known", "value": "pressure"},
        "target_ability": {"status": "known", "value": "pressure"},
        "target_item": {"status": "known_absent"},
        "terrain": {"status": "known", "value": "none"},
        "target_groundedness": {"status": "known", "value": "grounded"},
    }
    result = resolve_probabilistic_target_status_effect_capability(move=move, source_authority=source)
    assert result["status"] == "resolved", result
    assert result["probability"] == {"numerator": 30, "denominator": 100}
    assert result["effect"] == {"owner": "target", "condition": "paralysis"}


def test_phantom_and_shadow_force_remain_outside_bounded_terminal_family():
    for move_id in ("phantom-force", "shadow-force"):
        effect = resolve_canonical_standard_charge_turn_two_effect(move_id)
        assert effect["status"] == "unsupported"


def _next_turn_opponent_action_chain(move_id: str, *, self_speed: int, opponent_speed: int):
    self_stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": self_speed}
    opponent_stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": opponent_speed}
    handoff = _production_temporal_handoff(
        own_move="fly", opponent_move="razor-wind",
        self_final_stats=self_stats, opponent_final_stats=opponent_stats,
    )
    state = handoff["next_state"]; fingerprint = handoff["resulting_branch_fingerprint"]
    predictive = handoff["next_turn_predictive_mechanics_authority"]
    forced = materialize_detached_standard_charge_forced_continuation(next_decision_state=state, next_decision_fingerprint=fingerprint)
    opponent_owner = predictive["active_owners"]["opponent"]; self_owner = predictive["active_owners"]["self"]
    metadata = {
        "status": "resolved", "move_id": move_id,
        "category": "special" if move_id == "gust" else "physical",
        "power": 40, "accuracy": 100, "priority": 0,
        "type": "flying" if move_id == "gust" else "normal",
    }
    hypothetical = {"opponent": {"actor": opponent_owner, "target": self_owner, "action_id": f"opponent-{move_id}", "move_id": move_id, "canonical_move_metadata_authority": metadata}}
    intents = materialize_detached_next_turn_action_intents(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        hypothetical_actions=hypothetical, forced_continuation=forced,
    )
    assert intents["status"] == "resolved", intents
    order = materialize_detached_next_turn_action_order_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        predictive_mechanics=predictive, action_intents=intents,
        action_order_temporal_state_authority=handoff["next_turn_action_order_temporal_state_authority"],
    )
    ordinary = materialize_detached_next_turn_ordinary_attack_execution_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        predictive_mechanics=predictive, action_intents=intents, side="opponent",
    )
    charge = materialize_detached_standard_charge_turn_two_execution_authority(
        next_decision_state=state, next_decision_fingerprint=fingerprint,
        forced_continuation=forced, predictive_mechanics=predictive,
    )
    return handoff, order, ordinary, charge


def test_next_turn_faster_exception_still_sees_active_airborne_state():
    _handoff, order, ordinary, _charge = _next_turn_opponent_action_chain("gust", self_speed=50, opponent_speed=150)
    assert order["status"] == "resolved" and order["order"] == "opponent_first", order
    result = execute_detached_next_turn_ordinary_attack(execution_authority=ordinary)
    assert result["status"] == "resolved", result
    leaves = result["action_ledger"]["terminal_leaves"]
    assert leaves
    assert all(leaf["consequences"]["semi_invulnerable_targetability"]["outcome"] == "allowed_by_exact_exception" for leaf in leaves)
    assert ordinary["action"]["semi_invulnerable_charge_state_authority"]["state"] == "active"


def _recontract_semi(contract, actor_mechanics):
    auth=deepcopy(contract["caller_authentication"])
    auth["actor_mechanics"]=deepcopy(actor_mechanics)
    return materialize_standard_charge_terminal_execution_contract(
        execution_mode=contract["execution_mode"],
        source_state_fingerprint=contract["source_state_fingerprint"],
        decision_owner=contract["decision_owner"],actor=contract["actor"],target=contract["target"],
        action_id=contract["action_id"],move_id=contract["move_id"],canonical_terminal_effect=contract["canonical_terminal_effect"],
        actor_mechanics=actor_mechanics,target_mechanics=contract["target_mechanics"],
        attacker_held_item_effect_authority=contract["attacker_held_item_effect_authority"],
        target_held_item_effect_authority=contract["target_held_item_effect_authority"],
        target_sturdy_authority=contract["target_sturdy_authority"],target_focus_sash_authority=contract["target_focus_sash_authority"],
        attacker_life_orb_authority=contract["attacker_life_orb_authority"],caller_action_authority=contract["caller_action_authority"],
        caller_authentication=auth,semi_invulnerable_charge_state_authority=contract["semi_invulnerable_charge_state_authority"],
    )


def _fly_forced_contract():
    handoff=_production_temporal_handoff(own_move="fly",opponent_move="razor-wind")
    state=handoff["next_state"]; fp=handoff["resulting_branch_fingerprint"]
    forced=materialize_detached_standard_charge_forced_continuation(next_decision_state=state,next_decision_fingerprint=fp)
    authority=materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state,next_decision_fingerprint=fp,forced_continuation=forced,predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"])
    contract=materialize_detached_standard_charge_turn_two_terminal_execution_contract(execution_authority=authority,side="self")
    assert contract["status"]=="resolved",contract
    return contract


def test_retirement_reasons_cover_paralysis_confusion_and_faint():
    contract=_fly_forced_contract()

    paralyzed=deepcopy(contract["actor_mechanics"])
    paralyzed["condition"]={"status":"known_present","condition":"paralysis"}
    paralyzed["direct_mechanics"]["combatant"]["status"]="paralysis"
    result=execute_standard_charge_terminal_attack(execution_contract=_recontract_semi(contract,paralyzed))
    cancelled=[leaf for leaf in result["terminal_leaves"] if "cancelled_due_to_paralysis" in leaf["branch_path"]]
    assert cancelled and all(leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"]=="full_paralysis_cancellation" for leaf in cancelled)

    confused=deepcopy(contract["actor_mechanics"])
    confused["confusion_state"]={"status":"known_confused"}
    confused["confusion_progression"]={"status":"known","value":{"origin_id":"semi-confusion","prior_opportunities":0,"duration":3}}
    # The shared temporal fixture predates exact combatant identity transport;
    # bind the already-authenticated continuation owner for this focused gate proof.
    confused["direct_mechanics"]["combatant"]["pokemon_id"]=contract["actor"]["pokemon_id"]
    result=execute_standard_charge_terminal_attack(execution_contract=_recontract_semi(contract,confused))
    assert result["status"]=="resolved", (result.get("status"),result.get("reason"))
    self_hits=[leaf for leaf in result["terminal_leaves"] if "confusion_self_hit" in " ".join(str(x) for x in leaf["branch_path"])]
    assert self_hits and all(leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"]=="confusion_self_hit" for leaf in self_hits)

    fainted=deepcopy(contract["actor_mechanics"])
    fainted["current_hp"]["current_hp"]=0; fainted["fainted"]=True; fainted["direct_mechanics"]["combatant"]["current_hp"]=0
    result=execute_standard_charge_terminal_attack(execution_contract=_recontract_semi(contract,fainted))
    assert result["status"]=="resolved"
    leaf=result["terminal_leaves"][0]
    assert leaf["consequences"]["semi_invulnerable_state_retirement"]["reason"]=="actor_faint_prevents_continuation"


@pytest.mark.parametrize("incoming",("smack-down","thousand-arrows"))
def test_airborne_state_ending_exception_marks_exact_cancellation(incoming):
    snapshot,d0,_actor,_original_target,_action,state=_state_authority("fly")
    target=state["owner"]; attacker=d0["active_owners"]["opponent"]
    metadata={"move_id":incoming,"category":"physical","power":50,"type":"rock" if incoming=="smack-down" else "ground","accuracy":100,"priority":0}
    action,meta=_incoming(d0,incoming,metadata)
    authority=freeze_detached_semi_invulnerable_targetability_authority(strategy_d0=d0,runtime_snapshot=snapshot,incoming_action=action,incoming_move_metadata_authority=meta,attacker=attacker,target=target,semi_invulnerable_state_authority=state)
    assert authority["status"]=="resolved" and authority["outcome"]=="allowed_by_exact_exception"
    assert authority["exception_multiplier"]==1
    assert authority["state_cancel_after_successful_hit"] is True


def test_bounce_turn_two_paralysis_branches_and_mass_are_exact():
    handoff=_production_temporal_handoff(own_move="bounce",opponent_move="razor-wind",opponent_grounded=True)
    state=handoff["next_state"]; fingerprint=handoff["resulting_branch_fingerprint"]
    forced=materialize_detached_standard_charge_forced_continuation(next_decision_state=state,next_decision_fingerprint=fingerprint)
    authority=materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state,next_decision_fingerprint=fingerprint,forced_continuation=forced,predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"])
    result=execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    assert result["status"]=="resolved", result
    ledger=result["actions"]["self"]
    assert ledger["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    applied=[leaf for leaf in ledger["terminal_leaves"] if "secondary:paralysis" in leaf["branch_path"]]
    none=[leaf for leaf in ledger["terminal_leaves"] if "secondary:none" in leaf["branch_path"]]
    misses=[leaf for leaf in ledger["terminal_leaves"] if leaf["hit_state"]=="miss"]
    assert applied and none and misses
    assert all(leaf["consequences"]["secondary"]["condition"]=="paralysis" for leaf in applied)
    assert all(leaf["consequences"]["secondary"] is None for leaf in none+misses)
    applied_mass=sum((Fraction(x["probability"]["numerator"],x["probability"]["denominator"]) for x in applied),Fraction())
    eligible_mass=applied_mass+sum((Fraction(x["probability"]["numerator"],x["probability"]["denominator"]) for x in none),Fraction())
    assert applied_mass*10==eligible_mass*3


def test_next_turn_slower_action_sees_retired_state_after_forced_continuation():
    handoff, order, ordinary, charge = _next_turn_opponent_action_chain("tackle", self_speed=150, opponent_speed=50)
    assert order["status"] == "resolved" and order["order"] == "self_first", order
    first = execute_detached_standard_charge_turn_two_attacks(execution_authority=charge)
    assert first["status"] == "resolved", first
    first_leaf = first["actions"]["self"]["terminal_leaves"][0]
    overlay = materialize_detached_next_turn_pair_local_predictive_mechanics(
        next_decision_state=handoff["next_state"],
        next_decision_fingerprint=handoff["resulting_branch_fingerprint"],
        predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"],
        first_action_execution=charge,
        first_action_ledger=first,
        first_leaf_id=first_leaf["leaf_id"],
    )
    assert overlay["status"] == "resolved", overlay
    assert overlay["semi_invulnerable_state_retirement_authority"]["state_after"] == "inactive"
    second = execute_detached_next_turn_ordinary_attack(execution_authority=ordinary, pair_local_predictive_mechanics=overlay)
    assert second["status"] == "resolved", second
    assert second["action_ledger"]["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all("semi_invulnerable_targetability" not in leaf["consequences"] for leaf in second["action_ledger"]["terminal_leaves"])
