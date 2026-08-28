from copy import deepcopy

from llm.advisor_detached_intermediate_predictive_authority import (
    detached_intermediate_builder_inputs, freeze_detached_intermediate_predictive_authority,
)
from llm.advisor_detached_intermediate_paralysis_second_action_authority import (
    consume_detached_intermediate_paralysis_for_second_action, consume_detached_sleep_freeze_execution_for_second_action,
)
from llm.advisor_detached_predictive_intermediate_state import (
    freeze_detached_actor_neutral_root_predictive_authority,
    materialize_detached_predictive_intermediate_state,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    build_runtime_d0_native_damage_context, build_runtime_d0_strict_critical_hit_probability_assessment,
    build_runtime_d0_strict_hit_probability_assessment, freeze_runtime_d0_sparkling_aria_burn_clearing_authority, freeze_runtime_normal_formula_predictive_input,
    freeze_runtime_strategy_d0, resolve_runtime_d0_selectable_move_metadata_authority,
)
from llm.advisor_immediate_move_vs_move_action_pair import _normal_formula_ledger, materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from llm.advisor_exact_action_pair_descriptive_metrics import project_exact_immediate_action_pair_descriptive_metrics
from llm.advisor_substitute import update_substitute_state_context


MOVE = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}
SPARKLING_ARIA = {"move_id": "sparkling-aria", "category": "special", "power": 90, "type": "water", "accuracy": 100, "priority": 0, "target": "selected-pokemon", "effect_chance": 100, "ailment": "none"}


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


def test_exact_intermediate_paralysis_consumes_private_condition_and_branches_second_action():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    intermediate = _intermediate(d0)
    intermediate["active"]["opponent"]["hypothetical_condition"] = {
        "status": "known_present", "condition": "paralysis", "source": "exact_terminal_leaf_condition_effect",
    }
    authority = freeze_detached_intermediate_predictive_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate,
        actor=_owner(state, "opponent"), target=_owner(state, "self"),
        move_metadata_authority=_metadata_authority(d0),
    )
    consumed = consume_detached_intermediate_paralysis_for_second_action(
        intermediate_predictive_authority=authority,
    )
    assert consumed["status"] == "resolved"
    assert [(row["state"], row["conditional_probability"]) for row in consumed["second_action_execution_branches"]] == [
        ("cancelled_due_to_paralysis", {"numerator": 1, "denominator": 4}),
        ("executed", {"numerator": 3, "denominator": 4}),
    ]
    inputs = consumed["builder_inputs"]
    assert inputs["hypothetical_condition_authority"]["condition"] == "paralysis"
    assert inputs["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["condition"] == "paralysis"
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"
    native = build_runtime_d0_native_damage_context(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], move_metadata=MOVE)
    hit = build_runtime_d0_strict_hit_probability_assessment(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], selected_move=MOVE)
    crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=inputs["strategy_d0"], runtime_snapshot=inputs["runtime_snapshot"], attacker=inputs["attacker"], target=inputs["target"], move_metadata=MOVE)
    assert native["status"] == hit["status"] == crit["status"] == "resolved"
    assert consumed["paralysis_speed_semantics"] == "action_order_already_frozen_before_first_action"

    no_condition = freeze_detached_intermediate_predictive_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=_intermediate(d0),
        actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0),
    )
    assert consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=no_condition)["second_action_execution_branches"] == (
        {"execution_branch_id": "second_action:can_act", "state": "executed", "conditional_probability": {"numerator": 1, "denominator": 1}},
    )
    bad = deepcopy(authority)
    bad["intermediate_overrides"]["actor"]["condition"] = {"status": "known_present", "condition": "sleep", "source": "exact_terminal_leaf_condition_effect"}
    assert consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=bad)["status"] == "incomplete"
    stale = deepcopy(authority); stale["predictive_strategy_d0"]["decision_owner"] = _owner(state, "self")
    assert consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=stale)["status"] == "rejected"


def test_current_sleep_freeze_execution_authority_is_exact_and_hypothetical_status_stays_closed():
    state = _state(); state["opponent_side"]["pokemon"][0]["condition"] = "sleep"
    state["opponent_side"]["pokemon"][0]["condition_provenance"]["condition"] = "sleep"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    authority = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=_intermediate(d0), actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0))
    pending = {"status": "resolved", "schema_version": "runtime-d0-pending-status-action-execution-authority-v1", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "pending_actor": _owner(state, "opponent"), "pending_action_id": "opponent_attack:tackle", "pending_move_id": "tackle", "condition": "sleep", "execution_state": "blocked", "blocker": "sleep"}
    blocked = consume_detached_sleep_freeze_execution_for_second_action(intermediate_predictive_authority=authority, pending_action_id="opponent_attack:tackle", pending_status_execution_authority=pending)
    assert blocked["status"] == "resolved" and blocked["second_action_execution_branches"][0]["state"] == "cancelled_due_to_sleep"
    executable = consume_detached_sleep_freeze_execution_for_second_action(intermediate_predictive_authority=authority, pending_action_id="opponent_attack:tackle", pending_status_execution_authority={**pending, "execution_state": "executable", "blocker": None})
    assert executable["status"] == "resolved" and executable["second_action_execution_branches"][0]["state"] == "executed"
    assert consume_detached_sleep_freeze_execution_for_second_action(intermediate_predictive_authority=authority, pending_action_id="opponent_attack:tackle", pending_status_execution_authority=None)["status"] == "incomplete"
    hypothetical = _intermediate(d0); hypothetical["active"]["opponent"]["hypothetical_condition"] = {"status": "known_present", "condition": "freeze", "source": "exact_terminal_leaf_condition_effect"}
    detached = freeze_detached_intermediate_predictive_authority(strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=hypothetical, actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0))
    assert consume_detached_sleep_freeze_execution_for_second_action(intermediate_predictive_authority=detached, pending_action_id="opponent_attack:tackle", pending_status_execution_authority=pending)["status"] == "incomplete"


def test_exact_intermediate_paralysis_drives_facade_and_guts_without_current_mutation():
    def authority_for(d0, intermediate, metadata):
        return freeze_detached_intermediate_predictive_authority(
            strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate,
            actor=_owner(state, "opponent"), target=_owner(state, "self"),
            move_metadata_authority=metadata,
        )

    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    intermediate = _intermediate(d0)
    intermediate["active"]["opponent"]["hypothetical_condition"] = {"status": "known_present", "condition": "paralysis", "source": "exact_terminal_leaf_condition_effect"}
    facade = _metadata_authority(d0) | {"move_id": "facade", "metadata": {"move_id": "facade", "category": "physical", "power": 70, "type": "normal", "accuracy": 100, "priority": 0}}
    facade_inputs = consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=authority_for(d0, intermediate, facade))["builder_inputs"]
    facade_native = build_runtime_d0_native_damage_context(strategy_d0=facade_inputs["strategy_d0"], runtime_snapshot=facade_inputs["runtime_snapshot"], attacker=facade_inputs["attacker"], target=facade_inputs["target"], move_metadata=facade["metadata"])
    assert facade_native["status"] == "resolved"
    assert facade_native["native_evaluation"]["dynamic_power_evidence"]["effective_power"] == 140

    guts_state = _state(); guts_state["opponent_side"]["pokemon"][0]["current_ability"] = "guts"
    guts_snapshot = _snapshot(guts_state); guts_d0 = freeze_runtime_strategy_d0(runtime_snapshot=guts_snapshot, decision_owner=_owner(guts_state, "self"))
    guts_intermediate = _intermediate(guts_d0)
    guts_intermediate["active"]["opponent"]["hypothetical_condition"] = {"status": "known_present", "condition": "paralysis", "source": "exact_terminal_leaf_condition_effect"}
    guts_authority = freeze_detached_intermediate_predictive_authority(strategy_d0=guts_d0, runtime_snapshot=guts_snapshot, intermediate_state=guts_intermediate, actor=_owner(guts_state, "opponent"), target=_owner(guts_state, "self"), move_metadata_authority=_metadata_authority(guts_d0))
    guts_inputs = consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=guts_authority)["builder_inputs"]
    guts_native = build_runtime_d0_native_damage_context(strategy_d0=guts_inputs["strategy_d0"], runtime_snapshot=guts_inputs["runtime_snapshot"], attacker=guts_inputs["attacker"], target=guts_inputs["target"], move_metadata=MOVE)
    guts_crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=guts_inputs["strategy_d0"], runtime_snapshot=guts_inputs["runtime_snapshot"], attacker=guts_inputs["attacker"], target=guts_inputs["target"], move_metadata=MOVE)
    assert guts_native["status"] == guts_crit["status"] == "resolved"
    assert "ability_guts_status_attack_boost" in guts_native["native_evaluation"]["applied_damage_modifiers"]
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"
    assert guts_snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"


def test_exact_intermediate_burn_poison_and_toxic_reuse_existing_second_action_mechanics_without_mutation():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    def consumed(condition, move, *, ability=None, ability_side="opponent", actor_side="opponent", condition_side="opponent"):
        local_state = deepcopy(state)
        if ability is not None:
            local_state[f"{ability_side}_side"]["pokemon"][0]["current_ability"] = ability
        local_snapshot = _snapshot(local_state); local_d0 = freeze_runtime_strategy_d0(runtime_snapshot=local_snapshot, decision_owner=_owner(local_state, "self"))
        intermediate = _intermediate(local_d0)
        intermediate["active"][condition_side]["hypothetical_condition"] = {"status": "known_present", "condition": condition, "source": "exact_terminal_leaf_condition_effect"}
        metadata = _metadata_authority(local_d0) | {"move_id": move["move_id"], "metadata": move}
        target_side = "self" if actor_side == "opponent" else "opponent"
        authority = freeze_detached_intermediate_predictive_authority(strategy_d0=local_d0, runtime_snapshot=local_snapshot, intermediate_state=intermediate, actor=_owner(local_state, actor_side), target=_owner(local_state, target_side), move_metadata_authority=metadata)
        return consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=authority), local_snapshot

    burn_move = {"move_id": "tackle", "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}
    burn, burn_snapshot = consumed("burn", burn_move)
    assert burn["status"] == "resolved" and burn["second_action_execution_branches"][0]["conditional_probability"] == {"numerator": 1, "denominator": 1}
    burn_native = build_runtime_d0_native_damage_context(strategy_d0=burn["builder_inputs"]["strategy_d0"], runtime_snapshot=burn["builder_inputs"]["runtime_snapshot"], attacker=burn["builder_inputs"]["attacker"], target=burn["builder_inputs"]["target"], move_metadata=burn_move)
    assert "burn_physical_reduction" in burn_native["native_evaluation"]["applied_damage_modifiers"]
    assert burn_snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"

    facade_move = {"move_id": "facade", "category": "physical", "power": 70, "type": "normal", "accuracy": 100, "priority": 0}
    facade, _snapshot0 = consumed("burn", facade_move)
    facade_native = build_runtime_d0_native_damage_context(strategy_d0=facade["builder_inputs"]["strategy_d0"], runtime_snapshot=facade["builder_inputs"]["runtime_snapshot"], attacker=facade["builder_inputs"]["attacker"], target=facade["builder_inputs"]["target"], move_metadata=facade_move)
    assert facade_native["native_evaluation"]["dynamic_power_evidence"]["effective_power"] == 140

    hex_move = {"move_id": "hex", "category": "special", "power": 65, "type": "ghost", "accuracy": 100, "priority": 0}
    poison, _snapshot0 = consumed("poison", hex_move, actor_side="self", condition_side="opponent")
    poison_native = build_runtime_d0_native_damage_context(strategy_d0=poison["builder_inputs"]["strategy_d0"], runtime_snapshot=poison["builder_inputs"]["runtime_snapshot"], attacker=poison["builder_inputs"]["attacker"], target=poison["builder_inputs"]["target"], move_metadata=hex_move)
    assert poison_native["status"] == "resolved", (poison_native.get("reason"), poison_native.get("missing_inputs"), poison_native.get("native_evaluation"))
    assert poison_native["native_evaluation"]["dynamic_power_evidence"]["effective_power"] == 130
    assert poison["builder_inputs"]["runtime_snapshot"]["state"]["opponent_side"]["pokemon"][0]["condition"] == "poison"
    assert _snapshot0["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"

    venoshock_move = {"move_id": "venoshock", "category": "special", "power": 65, "type": "poison", "accuracy": 100, "priority": 0}
    toxic, _snapshot0 = consumed("toxic", venoshock_move, actor_side="self", condition_side="opponent")
    toxic_native = build_runtime_d0_native_damage_context(strategy_d0=toxic["builder_inputs"]["strategy_d0"], runtime_snapshot=toxic["builder_inputs"]["runtime_snapshot"], attacker=toxic["builder_inputs"]["attacker"], target=toxic["builder_inputs"]["target"], move_metadata=venoshock_move)
    assert toxic_native["status"] == "resolved"
    assert toxic_native["native_evaluation"]["dynamic_power_evidence"]["effective_power"] == 130

    merciless, _snapshot0 = consumed("poison", burn_move, ability="merciless", ability_side="self", actor_side="self", condition_side="opponent")
    merciless_crit = build_runtime_d0_strict_critical_hit_probability_assessment(strategy_d0=merciless["builder_inputs"]["strategy_d0"], runtime_snapshot=merciless["builder_inputs"]["runtime_snapshot"], attacker=merciless["builder_inputs"]["attacker"], target=merciless["builder_inputs"]["target"], move_metadata=burn_move)
    assert merciless_crit["status"] == "resolved"
    assert merciless_crit["critical_probability"] == {"numerator": 1, "denominator": 1}

    guts, _snapshot1 = consumed("toxic", burn_move, ability="guts")
    guts_native = build_runtime_d0_native_damage_context(strategy_d0=guts["builder_inputs"]["strategy_d0"], runtime_snapshot=guts["builder_inputs"]["runtime_snapshot"], attacker=guts["builder_inputs"]["attacker"], target=guts["builder_inputs"]["target"], move_metadata=burn_move)
    assert "ability_guts_status_attack_boost" in guts_native["native_evaluation"]["applied_damage_modifiers"]


def test_sparkling_aria_burn_clearing_is_a_detached_exact_terminal_effect() -> None:
    state = _state()
    opponent = state["opponent_side"]["pokemon"][0]
    opponent["condition"] = "burn"
    opponent["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "burn"}
    for side in ("self", "opponent"):
        state["substitute_state_context"] = update_substitute_state_context(
            context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side),
            state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1",
        )
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    authority = freeze_runtime_d0_sparkling_aria_burn_clearing_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata=SPARKLING_ARIA,
    )
    assert authority["status"] == "resolved", authority.get("reason")
    metadata = _metadata_authority(d0) | {"move_id": "sparkling-aria", "metadata": deepcopy(SPARKLING_ARIA)}
    ledger = _normal_formula_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=_owner(state, "self"), target=_owner(state, "opponent"), metadata_authority=metadata)
    assert ledger["status"] == "evaluable", ledger.get("reason")
    assert ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    effects = [leaf for leaf in ledger["terminal_leaves"] if leaf["consequences"]["secondary"] and leaf["consequences"]["secondary"].get("branch") == "effect"]
    assert effects
    for leaf in effects:
        removal = leaf["consequences"]["secondary"]["hypothetical_target_condition_removal"]
        assert removal == {
            "schema_version": "detached-hypothetical-target-condition-removal-v1",
            "condition_before": "burn", "condition_removed": "burn", "condition_after": "none",
            "removal_trigger": "successful_damaging_hit_target_survives",
            "provenance": "sparkling_aria_successful_damage_roll_burn_clearing_v1",
            "source_leaf_id": leaf["leaf_id"],
        }
        assert leaf["damage_roll"]["damage"] >= leaf["consequences"]["post_hit"]["actual_damage"]
    assert all(leaf["consequences"]["secondary"] is None for leaf in ledger["terminal_leaves"] if leaf["hit_state"] == "miss")
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "burn"

    no_burn_state = _state()
    for side in ("self", "opponent"):
        no_burn_state["substitute_state_context"] = update_substitute_state_context(
            context=no_burn_state.get("substitute_state_context"), session_id=no_burn_state["session_id"], owner=_owner(no_burn_state, side),
            state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1",
        )
    no_burn_snapshot = _snapshot(no_burn_state)
    no_burn_d0 = freeze_runtime_strategy_d0(runtime_snapshot=no_burn_snapshot, decision_owner=_owner(no_burn_state, "self"))
    no_burn = freeze_runtime_d0_sparkling_aria_burn_clearing_authority(
        strategy_d0=no_burn_d0, runtime_snapshot=no_burn_snapshot, attacker=_owner(no_burn_state, "self"), target=_owner(no_burn_state, "opponent"), move_metadata=SPARKLING_ARIA,
    )
    assert no_burn["status"] == "resolved" and no_burn["capability_resolution"]["effect_applicable"] is False
    stale = freeze_runtime_d0_sparkling_aria_burn_clearing_authority(
        strategy_d0=d0, runtime_snapshot=no_burn_snapshot, attacker=_owner(state, "self"), target=_owner(state, "opponent"), move_metadata=SPARKLING_ARIA,
    )
    assert stale["status"] == "rejected"


def test_sparkling_aria_exact_known_none_replaces_only_the_second_action_private_condition_view() -> None:
    state = _state()
    state["opponent_side"]["pokemon"][0]["condition"] = "burn"
    state["opponent_side"]["pokemon"][0]["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "burn"}
    for side in ("self", "opponent"):
        state["substitute_state_context"] = update_substitute_state_context(
            context=state.get("substitute_state_context"), session_id=state["session_id"], owner=_owner(state, side),
            state="known_inactive", substitute_hp=None, provenance="runtime_observed_substitute_state_v1",
        )
    snapshot = _snapshot(state)
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    sparkling = _metadata_authority(d0) | {"move_id": "sparkling-aria", "metadata": deepcopy(SPARKLING_ARIA)}
    first = _normal_formula_ledger(strategy_d0=d0, runtime_snapshot=snapshot, actor=_owner(state, "self"), target=_owner(state, "opponent"), metadata_authority=sparkling)
    leaf = next(row for row in first["terminal_leaves"] if row["consequences"]["secondary"] and row["consequences"]["secondary"].get("branch") == "effect")
    intermediate = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=leaf)
    condition = intermediate["active"]["opponent"]["hypothetical_condition"]
    assert condition["status"] == "known_none" and condition["source"] == "exact_terminal_leaf_condition_removal"
    second = freeze_detached_intermediate_predictive_authority(
        strategy_d0=d0, runtime_snapshot=snapshot, intermediate_state=intermediate,
        actor=_owner(state, "opponent"), target=_owner(state, "self"), move_metadata_authority=_metadata_authority(d0),
    )
    consumed = consume_detached_intermediate_paralysis_for_second_action(intermediate_predictive_authority=second)
    assert consumed["status"] == "resolved", consumed.get("reason")
    assert consumed["builder_inputs"]["hypothetical_condition_authority"] == {
        "status": "known_none", "conditions": {"actor": "none"},
        "provenance": "exact_terminal_leaf_condition_removal",
        "calculator_view": "exact_intermediate_condition_for_supported_status_dependent_damage",
    }
    private = consumed["builder_inputs"]["runtime_snapshot"]
    assert private["state"]["opponent_side"]["pokemon"][0]["condition"] == "none"
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["condition"] == "burn"
    native = build_runtime_d0_native_damage_context(
        strategy_d0=consumed["builder_inputs"]["strategy_d0"], runtime_snapshot=private,
        attacker=consumed["builder_inputs"]["attacker"], target=consumed["builder_inputs"]["target"], move_metadata=MOVE,
    )
    assert native["status"] == "resolved", native.get("reason")
    assert "burn_physical_reduction" not in native["native_evaluation"]["applied_damage_modifiers"]

    no_removal_leaf = deepcopy(leaf)
    no_removal_leaf["consequences"]["secondary"] = None
    no_removal = materialize_detached_predictive_intermediate_state(strategy_d0=d0, terminal_leaf=no_removal_leaf)
    assert no_removal["active"]["opponent"]["hypothetical_condition"]["condition"] == "burn"


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
    own_ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=own_first)
    opponent_ledger = normalize_exact_immediate_action_pair_outcome_ledger(pair=opponent_first)
    assert own_ledger["status"] == opponent_ledger["status"] == "evaluable", (own_ledger.get("reason"), opponent_ledger.get("reason"))
    assert own_ledger["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert len(own_ledger["terminal_leaves"]) == len(own_first["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair={"status": "incomplete", "reason": "missing"})["status"] == "incomplete"
    metrics = project_exact_immediate_action_pair_descriptive_metrics(ledger=own_ledger)
    assert metrics["status"] == "resolved" and metrics["ranking_influence"] == "none"
    assert metrics["own"]["ko_probability"] == {"numerator": 0, "denominator": 1}
    assert metrics["own"]["survival_probability"] == {"numerator": 1, "denominator": 1}
    assert metrics["joint_terminal_states"]["probability_mass"] == {"numerator": 1, "denominator": 1}
    assert project_exact_immediate_action_pair_descriptive_metrics(ledger={"status": "unsupported", "reason": "upstream"})["status"] == "unsupported"
    assert d0["decision_owner"] == own and snapshot["state"]["self_side"]["pokemon"][0]["current_hp"] == 100
