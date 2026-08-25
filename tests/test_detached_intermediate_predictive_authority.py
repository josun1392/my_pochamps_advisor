from copy import deepcopy

from llm.advisor_detached_intermediate_predictive_authority import (
    detached_intermediate_builder_inputs, freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context, build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment, freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_strategy_d0,
)


MOVE = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}


def _metadata_authority(d0: dict) -> dict:
    return {"status": "resolved", "move_id": "tackle", "metadata": deepcopy(MOVE), "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"])}


def _state() -> dict:
    state = create_unknown_bootstrap_battle_state("intermediate-authority", "self-a", "opponent-a")["state"]
    for side, types in (("self", ["normal"]), ("opponent", ["water"])):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, current_level=50, stat_stages={name: 0 for name in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}, condition="none", current_ability="pressure", known_item=None, current_type=types, current_crit_volatiles=[])
        pokemon["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "none"}
        pokemon["current_level_provenance"] = {"event_kind": "current_level_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_final_stats"] = {stat: {"value": 100, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}} for stat in ("attack", "defense", "special-attack", "special-defense", "speed")}
        state[f"{side}_side"]["side_conditions"] = []
        state[f"{side}_side"]["side_conditions_provenance"] = {"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"].update(weather="none", terrain="none")
    state["field"]["weather_provenance"] = {"event_kind": "current_weather_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["terrain_provenance"] = {"event_kind": "current_terrain_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["field"]["battle_format"] = "singles"
    state["field"]["battle_format_provenance"] = {"event_kind": "current_battle_format_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    return state


def _owner(state: dict, side: str) -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _intermediate(d0: dict, *, own_hp=70, target_hp=80, own_attack=1) -> dict:
    leaf = {"leaf_id": "hit/damage_roll:0", "candidate_id": "attack:tackle", "action_type": "attack", "branch_path": ({"branch": "hit", "conditional_probability": {"numerator": 1, "denominator": 1}},), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"roll_index": 0, "random_factor_percent": 85, "damage": 20}, "consequences": {"damage": 20, "own_final_hp": own_hp, "target_final_hp": target_hp, "target_ko": target_hp == 0, "self_fainted": own_hp == 0, "secondary": None}, "provenance": {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "attacker": d0["active_owners"]["self"], "target": d0["active_owners"]["opponent"], "move_id": "tackle"}}
    state = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    state["active"]["self"]["hypothetical_stages"]["attack"] = {"status": "known", "value": own_attack, "source": "test_exact_leaf"}
    return state


def test_reversed_actor_uses_exact_intermediate_hp_and_stages_through_existing_builders() -> None:
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    intermediate = _intermediate(d0, own_hp=61, target_hp=77, own_attack=2)
    authority = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0))
    inputs = detached_intermediate_builder_inputs(authority)
    assert authority["status"] == inputs["status"] == "resolved"
    assert inputs["strategy_d0"]["decision_owner"] == _owner(state, "opponent")
    assert inputs["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["current_hp"] == 61
    assert inputs["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["current_hp"] == 77
    assert inputs["runtime_snapshot"]["state"]["self_side"]["pokemon"][0]["stat_stages"]["attack"] == 2

    native = build_runtime_d0_native_damage_context(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], move_metadata=MOVE)
    normal = freeze_runtime_normal_formula_predictive_input(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], move_metadata=MOVE, native_damage_context=native)
    hit = build_runtime_d0_strict_hit_probability_assessment(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], selected_move=MOVE)
    crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], move_metadata=MOVE)
    assert native["status"] == normal["status"] == hit["status"] == crit["status"] == "resolved"
    assert native["snapshot_damage_input"]["battle_context"]["current_state"]["direct_mechanics_context"]["defender"]["current_hp"] == 61
    assert d0["decision_owner"] == _owner(state, "self")
    assert snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] == 100


def test_role_mismatch_fainted_actor_and_changed_condition_fail_closed() -> None:
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); intermediate = _intermediate(d0)
    bad = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=_owner(state, "self"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0))
    assert bad["status"] == "rejected"
    intermediate["active"]["opponent"]["hypothetical_fainted"]["value"] = True
    intermediate["active"]["opponent"]["hypothetical_hp"]["value"] = 0
    fainted = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0))
    assert fainted["status"] == "incomplete"


def test_own_actor_and_leaf_local_condition_are_preserved_without_current_authority_promotion() -> None:
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self")); intermediate = _intermediate(d0)
    own = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata_authority=_metadata_authority(d0))
    assert own["status"] == "resolved" and detached_intermediate_builder_inputs(own)["status"] == "resolved"

    intermediate["active"]["opponent"]["hypothetical_condition"] = {"status": "known_present", "condition": "paralysis", "source": "exact_terminal_leaf_condition_effect"}
    changed = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate, actor=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata_authority=_metadata_authority(d0))
    assert changed["status"] == "resolved"
    assert changed["intermediate_overrides"]["target"]["condition"]["condition"] == "paralysis"
    assert detached_intermediate_builder_inputs(changed)["status"] == "incomplete"
    stale = deepcopy(snapshot); stale["state"]["last_applied_observation_sequence"] = 2; stale["state_fingerprint"] = state_fingerprint(stale["state"])
    assert freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=stale, intermediate_state=intermediate, actor=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata_authority=_metadata_authority(d0))["status"] == "rejected"
