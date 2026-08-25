from copy import deepcopy

from llm.advisor_detached_intermediate_predictive_authority import (
    detached_intermediate_builder_inputs, freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_predictive_intermediate_state import (
    freeze_detached_actor_neutral_root_predictive_authority,
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context, build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment, freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_strategy_d0, resolve_runtime_d0_selectable_move_metadata_authority,
)
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_substitute import update_substitute_state_context


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


def test_opponent_root_leaf_maps_hp_and_preserves_original_d0_binding() -> None:
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own, opponent = _owner(state, "self"), _owner(state, "opponent")
    action = {
        "status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1",
        "action_id": "opponent_attack:tackle", "move_id": "tackle", "opponent_actor": opponent,
        "target_owner": own, "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"],
        "metadata_authority": {"status": "resolved", "move_id": "tackle", "metadata": deepcopy(MOVE)},
        "usability": {"status": "known_usable"}, "selectability": "selectable",
    }
    root = freeze_detached_actor_neutral_root_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_action=action)
    assert root["status"] == "resolved" and root["predictive_strategy_d0"]["decision_owner"] == opponent
    predictive = root["predictive_strategy_d0"]
    leaf = {
        "leaf_id": "hit/damage_roll:3", "candidate_id": "attack:tackle", "action_type": "attack",
        "branch_path": ({"branch": "hit", "conditional_probability": {"numerator": 1, "denominator": 1}},),
        "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "critical_state": "non_critical",
        "damage_roll": {"roll_index": 3, "random_factor_percent": 88, "damage": 20},
        "consequences": {"damage": 20, "own_final_hp": 81, "target_final_hp": 0, "target_ko": True, "self_fainted": False, "secondary": None},
        "provenance": {"session_id": predictive["session_id"], "source_runtime_fingerprint": predictive["source_runtime_fingerprint"], "source_branch_fingerprint": predictive["strategy_preview_fingerprint"], "decision_owner": opponent, "attacker": opponent, "target": own, "move_id": "tackle"},
    }
    materialized = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf, root_predictive_authority=root)
    assert materialized["status"] == "resolved"
    assert materialized["decision_owner"] == own
    assert materialized["active"]["self"]["hypothetical_hp"]["value"] == 0
    assert materialized["active"]["opponent"]["hypothetical_hp"]["value"] == 81
    assert materialized["active"]["self"]["hypothetical_fainted"]["value"] is True
    assert materialized["first_action"]["root_predictive_authority"]["root_actor"] == opponent
    assert state["self_side"]["pokemon"][0]["current_hp"] == 100

    effected = deepcopy(leaf); effected["consequences"] = {"damage": 20, "own_final_hp": 81, "target_final_hp": 80, "secondary": {"branch": "effect", "hypothetical_stage_effect": {"owner": "self", "stat": "attack", "resulting_stage": 1}, "hypothetical_target_condition": {"resulting_condition": "paralysis"}}}
    role_mapped = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=effected, root_predictive_authority=root)
    assert role_mapped["active"]["opponent"]["hypothetical_stages"]["attack"]["value"] == 1
    assert role_mapped["active"]["self"]["hypothetical_condition"]["condition"] == "paralysis"

    swapped = deepcopy(root); swapped["root_target"] = opponent
    assert materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf, root_predictive_authority=swapped)["status"] == "rejected"


def test_pair_executor_runs_ordinary_own_first_and_opponent_first_paths() -> None:
    state = _state()
    for side in ("self", "opponent"):
        state["substitute_state_context"] = update_substitute_state_context(context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side), state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1")
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    own, opponent = _owner(state, "self"), _owner(state, "opponent")
    own_meta = _metadata_authority(d0)
    own_meta.update({"schema_version": "canonical-normalized-move-metadata-authority-v1", "candidate_id": "attack:tackle", "active_attacker": own})
    own_action = {"action_id": "attack:tackle", "action_type": "attack", "identity": "tackle", "move_metadata_authority": own_meta}
    assert resolve_runtime_d0_selectable_move_metadata_authority(strategy_d0=d0, action=own_action)["status"] == "resolved"
    opponent_action = {"status": "resolved", "schema_version": "runtime-d0-opponent-known-move-action-authority-v1", "action_id": "opponent_attack:tackle", "action_type": "attack", "move_id": "tackle", "opponent_actor": opponent, "target_owner": own, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "metadata_authority": {"status": "resolved", "move_id": "tackle", "metadata": deepcopy(MOVE)}, "usability": {"status": "known_usable"}, "selectability": "selectable"}
    def order(value: str) -> dict:
        return {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": value, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "own_action_id": own_action["action_id"], "opponent_action_id": opponent_action["action_id"], "own_actor": own, "opponent_actor": opponent}
    own_first = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=order("own_first"))
    opponent_first = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent_action, action_order_authority=order("opponent_first"))
    assert own_first["status"] == opponent_first["status"] == "evaluable", (own_first.get("reason"), opponent_first.get("reason"))
    assert own_first["terminal_probability_mass"] == opponent_first["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert all(row["second_action"]["state"] == "executed" for row in own_first["terminal_branches"])
    assert all(row["second_action"]["state"] == "executed" for row in opponent_first["terminal_branches"])
    assert d0["decision_owner"] == own and snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] == 100
