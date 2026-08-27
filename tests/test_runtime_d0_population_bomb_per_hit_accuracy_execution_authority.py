from copy import deepcopy

from llm.advisor_runtime_d0_population_bomb_per_hit_accuracy_execution_authority import (
    SCHEMA_VERSION,
    freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state


def _state():
    state = create_unknown_bootstrap_battle_state("population-bomb-authority", "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, condition="none", current_ability="pressure", known_item=None, current_type=["normal"], current_crit_volatiles=[], stat_stages={"accuracy": 0, "evasion": 0})
        pokemon["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["known_item_provenance"] = {"event_kind": "current_item_observed", "trust": "user_confirmed_observation", "turn_number": 1, "status": "known_absent"}
        pokemon["current_type_provenance"] = {"event_kind": "current_type_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        pokemon["current_crit_volatiles_provenance"] = {"event_kind": "current_crit_volatiles_observed", "trust": "user_confirmed_observation", "turn_number": 1}
        state[f"{side}_side"].update(side_conditions=[], side_conditions_provenance={"event_kind": "current_side_conditions_observed", "trust": "user_confirmed_observation", "turn_number": 1})
    return state


def _owner(state):
    return {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state):
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _action(d0, **overrides):
    move = {"move_id": "population-bomb", "category": "physical", "power": 20, "type": "normal", "accuracy": 90, "priority": 0, "min_hits": 10, "max_hits": 10, "multiaccuracy": True}
    move.update(overrides)
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": "attack:population-bomb", "move_id": "population-bomb", "metadata": move, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    return {"action_id": "attack:population-bomb", "action_type": "attack", "identity": "population-bomb", "move_metadata_authority": authority}


def test_canonical_base_population_bomb_freezes_ten_independent_accuracy_attempts():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))
    assert result["status"] == "resolved" and result["schema_version"] == SCHEMA_VERSION
    assert result["maximum_attempt_execution"] == {"status": "resolved", "maximum_attempts": 10, "semantics": "canonical_fixed_ten_attempt_multiaccuracy"}
    accuracy = result["per_attempt_accuracy_execution"]
    assert accuracy["semantics"] == "independent_accuracy_check_per_attempt_stop_on_first_miss"
    assert accuracy["hit_probability"] == {"numerator": 9, "denominator": 10}
    assert accuracy["miss_probability"] == {"numerator": 1, "denominator": 10}
    assert accuracy["root_mass"] == {"numerator": 1, "denominator": 1}
    assert result["execution_exclusions"]["action_level_accuracy"] == "forbidden"


def test_relevant_or_unknown_count_modifiers_and_noncanonical_metadata_fail_closed():
    state = _state(); pokemon = state["self_side"]["pokemon"][0]; pokemon["current_ability"] = "skill-link"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))
    assert result["status"] == "unsupported" and result["reason"] == "population_bomb_skill_link_requires_separate_execution_authority"

    state = _state(); pokemon = state["self_side"]["pokemon"][0]; pokemon["known_item"] = "loaded-dice"; pokemon["known_item_provenance"]["status"] = "known"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))
    assert result["status"] == "unsupported" and result["reason"] == "population_bomb_loaded_dice_requires_separate_execution_authority"

    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    assert freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, multiaccuracy=False))["status"] == "unsupported"
    assert freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, min_hits=None))["status"] == "incomplete"


def test_stale_and_metadata_binding_conflicts_reject_without_mutation():
    state = _state(); original = deepcopy(state); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state)); action = _action(d0)
    result = freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    assert result["status"] == "resolved" and state == original
    state["self_side"]["pokemon"][0]["current_hp"] = 1
    assert freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), action=action)["status"] == "rejected"
    conflicting = deepcopy(action); conflicting["move_metadata_authority"]["metadata"]["move_id"] = "tackle"
    assert freeze_runtime_d0_population_bomb_per_hit_accuracy_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=conflicting)["status"] == "rejected"
