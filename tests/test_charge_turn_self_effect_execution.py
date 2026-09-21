from copy import deepcopy
from fractions import Fraction

import pytest

from advisor.canonical_standard_charge_turn_two_effects import resolve_canonical_standard_charge_turn_two_effect
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_standard_charge_start import (
    materialize_detached_standard_charge_start,
    validate_pair_compatible_standard_charge_leaf,
)
from llm.advisor_detached_standard_charge_forced_continuation import materialize_detached_standard_charge_forced_continuation
from llm.advisor_detached_standard_charge_turn_two_attack_execution import (
    execute_detached_standard_charge_turn_two_attacks,
    materialize_detached_standard_charge_turn_two_execution_authority,
    materialize_detached_standard_charge_turn_two_terminal_execution_contract,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    execute_runtime_d0_standard_charge_power_herb_skip,
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
    materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract,
)
from llm.advisor_runtime_d0_standard_charge_start_readiness_authority import freeze_runtime_d0_standard_charge_start_readiness_authority
from llm.advisor_standard_charge_turn_self_stage_effect import (
    freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority,
    validate_runtime_d0_standard_charge_turn_self_stage_effect_authority,
)
from llm.advisor_standard_charge_terminal_execution import (
    execute_standard_charge_terminal_attack,
    validate_standard_charge_terminal_execution_contract,
)
from llm.advisor_runtime_strategy_d0 import build_runtime_d0_native_damage_context, freeze_runtime_strategy_d0
from llm.advisor_next_turn_predictive_mechanics_authority import materialize_next_turn_predictive_mechanics_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from tests.test_runtime_d0_standard_charge_terminal_mechanics_authority import _ready, _refresh
from tests.test_detached_intermediate_predictive_authority import _owner
from tests.test_standard_charge_start_immediate_pair_integration import _own_action, _opponent_action, _order, _with_terminal_mechanics_facts, _complete_state, _state as _pair_state, _snapshot as _pair_snapshot
from tests.test_detached_next_turn_action_order_temporal_state import _production_temporal_handoff
from tests.test_standard_charge_turn_two_ordered_pair_core import _runtime_fixture

MOVES = ("meteor-beam", "skull-bash")


def _case(move_id="meteor-beam", *, stage=0, power_herb=False, hp=100, condition=None):
    state, _s0, _d0 = _ready()
    actor_raw = state["self_side"]["pokemon"][0]
    stat = "special-attack" if move_id == "meteor-beam" else "defense"
    actor_raw["stat_stages"][stat] = stage
    if power_herb:
        actor_raw["known_item"] = "power-herb"
        actor_raw["known_item_provenance"] = {"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known"}
    actor_raw["current_hp"] = hp
    actor_raw["fainted"] = hp == 0
    if condition is not None:
        actor_raw["condition"] = condition
        actor_raw["condition_provenance"] = {"event_kind":"current_condition_observed","trust":"user_confirmed_observation","condition":condition,"turn_number":1}
        if condition in {"sleep", "freeze"}:
            owner = {"session_id":state["session_id"],"side":"self","slot_index":0,"pokemon_id":actor_raw["pokemon_id"]}
            actor_raw["champions_status_progression"] = {
                "schema_version":"champions-sleep-freeze-progression-v1",
                "owner":owner,
                "condition":condition,
                "origin_id":f"{condition}:self-effect:1",
                "established_turn":1,
                "prior_attempts":0,
                "sleep_duration":3 if condition=="sleep" else None,
                "condition_observation":deepcopy(actor_raw["condition_provenance"]),
                "observed_turn":1,
                "provenance":"observed_champions_status_progression_v1",
            }
    snapshot, d0 = _refresh(state)
    actor, target = _owner(state, "self"), _owner(state, "opponent")
    action = _own_action(d0, actor, move_id)
    return state, snapshot, d0, actor, target, action


@pytest.mark.parametrize(("move_id","power","category","type_","stat"), [
    ("meteor-beam",120,"special","rock","special-attack"),
    ("skull-bash",130,"physical","normal","defense"),
])
def test_canonical_and_stage_authority(move_id,power,category,type_,stat):
    _state0,snapshot,d0,actor,target,action=_case(move_id)
    effect=resolve_canonical_standard_charge_turn_two_effect(move_id)
    assert effect["status"]=="resolved"
    assert (effect["move"]["power"],effect["move"]["category"],effect["move"]["type"],effect["move"]["accuracy"])==(power,category,type_,90 if move_id=="meteor-beam" else 100)
    authority=freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert authority["status"]=="resolved", authority
    assert authority["stat"]==stat and authority["delta"]==1
    assert authority["previous_stage"]==0 and authority["resulting_stage"]==1
    assert authority["timing"]=="before_charge_move_event"


@pytest.mark.parametrize("move_id",MOVES)
def test_ordinary_charge_start_carries_immediate_stage_effect(move_id):
    _state0,snapshot,d0,actor,target,action=_case(move_id)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert readiness["outcome"]=="charge_start_ready"
    result=materialize_detached_standard_charge_start(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,readiness_authority=readiness)
    assert result["status"]=="resolved", result
    effect=result["action_leaf"]["consequences"]["charge_turn_self_stage_effect"]
    stat="special-attack" if move_id=="meteor-beam" else "defense"
    assert (effect["stat"],effect["previous_stage"],effect["resulting_stage"])==(stat,0,1)
    intermediate=materialize_detached_predictive_intermediate_state(strategy_d0=d0,terminal_leaf=result["action_leaf"])
    assert intermediate["status"]=="resolved", intermediate
    assert intermediate["active"]["self"]["hypothetical_stages"][stat]["value"]==1


@pytest.mark.parametrize("move_id",MOVES)
def test_stage_cap_six_remains_six_and_charge_proceeds(move_id):
    _state0,snapshot,d0,actor,target,action=_case(move_id,stage=6)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    result=materialize_detached_standard_charge_start(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,readiness_authority=readiness)
    assert result["status"]=="resolved", result
    effect=result["action_leaf"]["consequences"]["charge_turn_self_stage_effect"]
    assert effect["previous_stage"]==effect["resulting_stage"]==6


@pytest.mark.parametrize("move_id",MOVES)
def test_power_herb_executes_with_stage_and_item_transport(move_id):
    _state0,snapshot,d0,actor,target,action=_case(move_id,power_herb=True)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    assert readiness["outcome"]=="power_herb_charge_skip_ready"
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":move_id},readiness_authority=readiness)
    assert authority["status"]=="resolved", authority
    contract=materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract(execution_authority=authority)
    assert contract["status"]=="resolved", contract
    assert contract["charge_turn_self_stage_effect_authority"]["resulting_stage"]==1
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved", kernel
    assert kernel["terminal_probability_mass"]=={"numerator":1,"denominator":1}
    executing=[x for x in kernel["terminal_leaves"] if not x["consequences"].get("execution_failure") and not x["consequences"].get("selected_move_does_not_execute")]
    assert executing
    assert all("charge_turn_self_stage_effect" in x["consequences"] and "power_herb_consumption" in x["consequences"] for x in executing)
    leaf=executing[0]
    intermediate=materialize_detached_predictive_intermediate_state(strategy_d0=d0,terminal_leaf=leaf)
    assert intermediate["status"]=="resolved", intermediate
    stat="special-attack" if move_id=="meteor-beam" else "defense"
    assert intermediate["active"]["self"]["hypothetical_stages"][stat]["value"]==1
    assert intermediate["active"]["self"]["hypothetical_item"]["status"]=="known_absent"


def test_power_herb_meteor_damage_uses_boosted_special_attack():
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam",power_herb=True,stage=0)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    _s1,snapshot2,d02,actor2,target2,action2=_case("meteor-beam",power_herb=True,stage=-1)
    readiness2=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d02,runtime_snapshot=snapshot2,action=action2,actor=actor2,target=target2)
    authority2=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d02,runtime_snapshot=snapshot2,action=action2,actor=actor2,target=target2,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness2)
    kernel2=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority2)
    max0=max(x["consequences"].get("raw_damage",0) for x in kernel["terminal_leaves"])
    maxm1=max(x["consequences"].get("raw_damage",0) for x in kernel2["terminal_leaves"])
    assert max0 > maxm1


def test_power_herb_fainted_gate_has_no_boost_or_consumption():
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam",power_herb=True,hp=0)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    assert authority["status"]=="resolved", (authority.get("status"),authority.get("reason"))
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved", kernel
    leaf=kernel["terminal_leaves"][0]
    assert "charge_turn_self_stage_effect" not in leaf["consequences"]
    assert "power_herb_consumption" not in leaf["consequences"]


def test_power_herb_paralysis_cancel_vs_execute_semantics():
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam",power_herb=True,condition="paralysis")
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    cancelled=[x for x in kernel["terminal_leaves"] if x["consequences"].get("execution_failure")=="cancelled_due_to_paralysis"]
    executed=[x for x in kernel["terminal_leaves"] if x["consequences"].get("execution_failure") is None]
    assert cancelled and executed
    assert sum(Fraction(x["probability"]["numerator"],x["probability"]["denominator"]) for x in cancelled)==Fraction(1,8)
    assert all("charge_turn_self_stage_effect" not in x["consequences"] and "power_herb_consumption" not in x["consequences"] for x in cancelled)
    assert all("charge_turn_self_stage_effect" in x["consequences"] and "power_herb_consumption" in x["consequences"] for x in executed)


def _ordinary_first_pair(move_id):
    state=_with_terminal_mechanics_facts(_complete_state(_pair_state()))
    snapshot=_pair_snapshot(state)
    d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self"))
    own=_own_action(d0,d0["active_owners"]["self"],move_id)
    opp=_opponent_action(d0,"tackle")
    pair=materialize_immediate_move_vs_move_action_pair(
        strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opp,
        action_order_authority=_order(d0,own,opp,"own_first"),
    )
    assert pair["status"]=="evaluable", (pair.get("status"),pair.get("reason"))
    return pair, d0


def test_skull_bash_first_defense_boost_reduces_same_turn_physical_second_action():
    skull,_skull_d0=_ordinary_first_pair("skull-bash")
    neutral,_neutral_d0=_ordinary_first_pair("razor-wind")
    skull_damage=[b["second_action"]["leaf"]["consequences"]["damage"] for b in skull["terminal_branches"] if b["second_action"]["state"]=="executed" and b["second_action"]["leaf"].get("critical_state")=="non_critical"]
    neutral_damage=[b["second_action"]["leaf"]["consequences"]["damage"] for b in neutral["terminal_branches"] if b["second_action"]["state"]=="executed" and b["second_action"]["leaf"].get("critical_state")=="non_critical"]
    assert skull_damage and neutral_damage
    assert max(skull_damage) < max(neutral_damage)
    assert all(b["first_action_leaf"]["consequences"]["charge_turn_self_stage_effect"]["resulting_stage"]==1 for b in skull["terminal_branches"])


def test_meteor_first_pair_leaf_projects_spa_plus_one_before_pending_action():
    pair,d0=_ordinary_first_pair("meteor-beam")
    for branch in pair["terminal_branches"]:
        leaf=branch["first_action_leaf"]
        assert leaf["consequences"]["charge_turn_self_stage_effect"]["stat"]=="special-attack"
        intermediate=materialize_detached_predictive_intermediate_state(
            strategy_d0=d0, terminal_leaf=leaf,
        )
        assert intermediate["status"]=="resolved", intermediate
        assert intermediate["active"]["self"]["hypothetical_stages"]["special-attack"]["value"]==1


def test_pair_second_action_ko_has_no_stage_or_charge():
    state=_with_terminal_mechanics_facts(_complete_state(_pair_state()))
    actor_raw=state["self_side"]["pokemon"][0]
    actor_raw["current_hp"]=1; actor_raw["max_hp"]=100; actor_raw["fainted"]=False
    snapshot=_pair_snapshot(state)
    d0=freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=_owner(state,"self"))
    own=_own_action(d0,d0["active_owners"]["self"],"meteor-beam")
    opp=_opponent_action(d0,"tackle")
    pair=materialize_immediate_move_vs_move_action_pair(strategy_d0=d0,runtime_snapshot=snapshot,own_action=own,opponent_action=opp,action_order_authority=_order(d0,own,opp,"opponent_first"))
    assert pair["status"]=="evaluable", (pair.get("status"),pair.get("reason"))
    cancelled=[b for b in pair["terminal_branches"] if b["second_action"]["state"]=="cancelled_due_to_faint"]
    assert cancelled
    assert all("charge_turn_self_stage_effect" not in b["first_action_leaf"]["consequences"] for b in cancelled)


@pytest.mark.parametrize("move_id",MOVES)
def test_generic_raw_guard_stays_closed(move_id):
    _state0,snapshot,d0,actor,target,_action=_case(move_id)
    result=build_runtime_d0_native_damage_context(strategy_d0=d0,runtime_snapshot=snapshot,attacker=actor,target=target,move_metadata=resolve_canonical_standard_charge_turn_two_effect(move_id)["move"])
    assert result["status"]=="incomplete"
    assert result["reason"]=="two_turn_execution_unrepresented"


def test_charge_start_and_self_stage_authority_tampering_rejects():
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam")
    authority=freeze_runtime_d0_standard_charge_turn_self_stage_effect_authority(
        strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,
    )
    forged=deepcopy(authority); forged["resulting_stage"]=6
    assert validate_runtime_d0_standard_charge_turn_self_stage_effect_authority(
        authority=forged,strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,
    ) is not None
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(
        strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,
    )
    start=materialize_detached_standard_charge_start(
        strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,readiness_authority=readiness,
    )
    leaf=deepcopy(start["action_leaf"])
    leaf["consequences"]["charge_turn_self_stage_effect"]["resulting_stage"]=6
    assert validate_pair_compatible_standard_charge_leaf(leaf) is not None


def test_power_herb_contract_stage_tampering_rejects():
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam",power_herb=True)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    contract=materialize_runtime_d0_standard_charge_power_herb_terminal_execution_contract(execution_authority=authority)
    forged=deepcopy(contract)
    forged["charge_turn_self_stage_effect_authority"]["resulting_stage"]=6
    assert validate_standard_charge_terminal_execution_contract(forged) is not None
    assert execute_standard_charge_terminal_attack(execution_contract=forged)["status"]=="rejected"


def _power_herb_status_case(condition):
    _state0,snapshot,d0,actor,target,action=_case("meteor-beam",power_herb=True,condition=condition)
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    assert authority["status"]=="resolved", authority
    return execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)


@pytest.mark.parametrize("condition",("sleep","freeze"))
def test_sleep_freeze_cancelled_branches_never_boost_or_consume(condition):
    kernel=_power_herb_status_case(condition)
    assert kernel["status"]=="resolved", kernel
    cancelled=[x for x in kernel["terminal_leaves"] if x["consequences"].get("execution_failure") in {"cancelled_sleep","cancelled_freeze"}]
    assert cancelled
    assert all("charge_turn_self_stage_effect" not in x["consequences"] and "power_herb_consumption" not in x["consequences"] for x in cancelled)
    executed=[x for x in kernel["terminal_leaves"] if x["consequences"].get("execution_failure") is None and not x["consequences"].get("selected_move_does_not_execute")]
    if executed:
        assert all("charge_turn_self_stage_effect" in x["consequences"] and "power_herb_consumption" in x["consequences"] for x in executed)


def test_confusion_self_hit_has_no_boost_or_power_herb_consumption():
    state,_s0,_d00=_ready()
    raw=state["self_side"]["pokemon"][0]
    raw["known_item"]="power-herb"
    raw["known_item_provenance"]={"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known"}
    raw["current_confusion"]="confused"
    raw["confusion_provenance"]={"event_kind":"current_confusion_observed","trust":"user_confirmed_observation","turn_number":1,"state":"confused"}
    actor={"session_id":state["session_id"],"side":"self","slot_index":0,"pokemon_id":raw["pokemon_id"]}
    raw["champions_confusion_progression"]={
        "schema_version":"champions-confusion-progression-v1","owner":deepcopy(actor),"state":"confused",
        "origin_id":"confusion:self-effect:1","established_turn":1,"prior_opportunities":0,"duration":3,
        "confusion_observation":deepcopy(raw["confusion_provenance"]),"observed_turn":1,
        "provenance":"observed_champions_confusion_progression_v1",
    }
    snapshot,d0=_refresh(state)
    target=_owner(state,"opponent"); action=_own_action(d0,actor,"meteor-beam")
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    assert authority["status"]=="resolved", authority
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved", kernel
    self_hit=[x for x in kernel["terminal_leaves"] if x["consequences"].get("selected_move_does_not_execute") is True]
    executed=[x for x in kernel["terminal_leaves"] if x["consequences"].get("execution_failure") is None and not x["consequences"].get("selected_move_does_not_execute")]
    assert self_hit and executed
    assert all("charge_turn_self_stage_effect" not in x["consequences"] and "power_herb_consumption" not in x["consequences"] for x in self_hit)
    assert all("charge_turn_self_stage_effect" in x["consequences"] and "power_herb_consumption" in x["consequences"] for x in executed)


@pytest.mark.parametrize(("survival_key","ability","item"),(
    ("sturdy_survival","sturdy",None),
    ("focus_sash_survival","pressure","focus-sash"),
))
def test_power_herb_meteor_reuses_sturdy_and_focus_sash(survival_key,ability,item):
    state,_s0,_d00=_ready()
    actor_raw=state["self_side"]["pokemon"][0]
    actor_raw["known_item"]="power-herb"
    actor_raw["known_item_provenance"]={"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known"}
    target_raw=state["opponent_side"]["pokemon"][0]
    target_raw["current_hp"]=100; target_raw["max_hp"]=100; target_raw["fainted"]=False
    target_raw["current_final_stats"]["special-defense"]["value"]=1
    target_raw["current_ability"]=ability
    target_raw["current_ability_provenance"]={"event_kind":"current_ability_observed","trust":"user_confirmed_observation","turn_number":1}
    if ability=="sturdy":
        state["ability_applicability_context"]=build_ability_applicability_context(
            session_id=state["session_id"],
            source={"side":"opponent","slot_index":0,"pokemon_id":target_raw["pokemon_id"]},
            ability_id="sturdy", status="applicable",
        )
    target_raw["known_item"]=item
    target_raw["known_item_provenance"]={"event_kind":"current_item_observed","trust":"user_confirmed_observation","turn_number":1,"status":"known" if item else "known_absent"}
    snapshot,d0=_refresh(state); actor,target=_owner(state,"self"),_owner(state,"opponent"); action=_own_action(d0,actor,"meteor-beam")
    readiness=freeze_runtime_d0_standard_charge_start_readiness_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target)
    authority=freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(strategy_d0=d0,runtime_snapshot=snapshot,action=action,actor=actor,target=target,move_metadata={"move_id":"meteor-beam"},readiness_authority=readiness)
    kernel=execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=authority)
    assert kernel["status"]=="resolved", kernel
    applied=[x for x in kernel["terminal_leaves"] if isinstance(x["consequences"].get(survival_key),dict) and x["consequences"][survival_key].get("outcome") in {"applied","activated"}]
    assert applied and all(x["consequences"]["target_final_hp"]==1 for x in applied)


def test_ordinary_turn_two_meteor_preserves_real_life_orb_support():
    handoff=_production_temporal_handoff(own_move="meteor-beam",opponent_move="razor-wind",self_item="life-orb")
    state=deepcopy(handoff["next_state"])
    field=state.setdefault("field",{})
    field["magic_room_status"]="inactive"
    field["magic_room_status_provenance"]={
        "event_kind":"magic_room_field_observed","trust":"user_confirmed_observation",
        "source_observation_id":"turn-two-life-orb-magic-room","source_sequence":1,
    }
    current=state.setdefault("current_state",{}).setdefault("field_state_context",{}).setdefault("current_field",{})
    current["magic_room_status"]="inactive"
    current["magic_room_status_provenance"]=deepcopy(field["magic_room_status_provenance"])
    fingerprint=fingerprint_transition_preview_state(state)
    predictive=materialize_next_turn_predictive_mechanics_authority(
        next_decision_state=state,next_decision_fingerprint=fingerprint,
        source_post_eot_fingerprint=handoff["next_turn_predictive_mechanics_authority"]["source_post_eot_fingerprint"],
    )
    assert predictive["status"]=="resolved", predictive
    forced=materialize_detached_standard_charge_forced_continuation(next_decision_state=state,next_decision_fingerprint=fingerprint)
    authority=materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state,next_decision_fingerprint=fingerprint,forced_continuation=forced,predictive_mechanics=predictive)
    contract=materialize_detached_standard_charge_turn_two_terminal_execution_contract(execution_authority=authority,side="self")
    assert contract["status"]=="resolved", contract
    assert contract["attacker_life_orb_authority"]["damage_modifier"]["applies"] is True
    result=execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    leaves=result["actions"]["self"]["terminal_leaves"]
    assert any(x["consequences"].get("life_orb",{}).get("outcome")=="recoiled" for x in leaves)


@pytest.mark.parametrize("move_id",MOVES)
def test_turn_two_uses_transport_and_does_not_carry_second_boost(move_id):
    handoff=_production_temporal_handoff(own_move=move_id,opponent_move="razor-wind")
    state=handoff["next_state"]; fingerprint=handoff["resulting_branch_fingerprint"]
    forced=materialize_detached_standard_charge_forced_continuation(next_decision_state=state,next_decision_fingerprint=fingerprint)
    assert forced["status"]=="resolved", forced
    authority=materialize_detached_standard_charge_turn_two_execution_authority(next_decision_state=state,next_decision_fingerprint=fingerprint,forced_continuation=forced,predictive_mechanics=handoff["next_turn_predictive_mechanics_authority"])
    assert authority["status"]=="resolved", authority
    contract=materialize_detached_standard_charge_turn_two_terminal_execution_contract(execution_authority=authority,side="self")
    assert contract["status"]=="resolved", contract
    assert "charge_turn_self_stage_effect_authority" not in contract
    stat="special-attack" if move_id=="meteor-beam" else "defense"
    _snap0,d00,_own0,_opp0,_order0,_charge0=_runtime_fixture()
    initial=d00["current_stage_authority"]["self"]["stages"][stat]["value"]
    assert contract["actor_mechanics"]["current_stages"]["values"][stat]==min(6, initial+1)
    result=execute_detached_standard_charge_turn_two_attacks(execution_authority=authority)
    assert result["status"]=="resolved", result
    assert result["actions"]["self"]["terminal_probability_mass"]=={"numerator":1,"denominator":1}
