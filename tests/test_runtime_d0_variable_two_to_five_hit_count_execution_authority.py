from copy import deepcopy

import pytest

from llm.advisor_runtime_d0_variable_two_to_five_hit_count_execution_authority import (
    SCHEMA_VERSION, freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority,
)
from llm.advisor_runtime_d0_variable_multi_hit_count_modifier_authority import (
    SCHEMA_VERSION as MODIFIER_SCHEMA,
    freeze_runtime_d0_variable_multi_hit_count_modifier_authority,
)
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_d0_critical_hit_authority,
    freeze_runtime_strategy_d0,
)
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state


def _state():
    state = create_unknown_bootstrap_battle_state("variable-two-to-five", "attacker", "target")["state"]
    for side in ("self", "opponent"):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon.update(current_hp=100, max_hp=100, fainted=False, condition="none", current_ability="pressure", known_item=None, current_type=["normal"], current_crit_volatiles=[])
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


def _action(d0, move_id="bullet-seed", **metadata):
    move = {"move_id": move_id, "category": "physical", "power": 25, "type": "grass", "accuracy": 100, "priority": 0, "min_hits": 2, "max_hits": 5}
    move.update(metadata)
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": move, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


@pytest.mark.parametrize("move_id, move_type", [("bullet-seed", "grass"), ("rock-blast", "rock")])
def test_canonical_variable_moves_freeze_exact_standard_count_and_per_hit_crit(move_id, move_type):
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, move_id, type=move_type))
    assert result["status"] == "resolved" and result["schema_version"] == SCHEMA_VERSION
    assert result["hit_count_execution"]["distribution"] == (
        {"hit_count": 2, "probability": {"numerator": 7, "denominator": 20}},
        {"hit_count": 3, "probability": {"numerator": 7, "denominator": 20}},
        {"hit_count": 4, "probability": {"numerator": 3, "denominator": 20}},
        {"hit_count": 5, "probability": {"numerator": 3, "denominator": 20}},
    )
    assert result["hit_count_execution"]["root_mass"] == {"numerator": 1, "denominator": 1}
    assert result["per_hit_critical_execution"]["semantics"] == "independent_canonical_critical_roll_per_hit"


def test_fixed_two_missing_and_other_multi_hit_families_fail_closed():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    assert freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, "double-hit", min_hits=2, max_hits=2, power=40, type="normal"))["reason"] == "multi_hit_family_not_canonical_variable_two_to_five"
    assert freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, min_hits=None))["reason"] == "variable_multi_hit_count_metadata_missing"
    assert freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, "population-bomb", min_hits=2, max_hits=5, multiaccuracy=True))["reason"] == "variable_multi_hit_move_not_in_supported_execution_catalog"


@pytest.mark.parametrize(
    "field, value, expected_modifier, expected_distribution",
    [
        ("current_ability", "skill-link", "skill_link", ((5, 1, 1),)),
        ("known_item", "loaded-dice", "loaded_dice", ((4, 1, 2), (5, 1, 2))),
    ],
)
def test_skill_link_and_loaded_dice_freeze_exact_modifier_distributions(field, value, expected_modifier, expected_distribution):
    state = _state(); pokemon = state["self_side"]["pokemon"][0]; pokemon[field] = value
    if field == "known_item": pokemon["known_item_provenance"]["status"] = "known"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))
    assert result["status"] == "resolved"
    assert result["hit_count_modifier_authority"]["schema_version"] == MODIFIER_SCHEMA
    assert result["hit_count_modifier_authority"]["modifier"] == expected_modifier
    assert tuple((row["hit_count"], row["probability"]["numerator"], row["probability"]["denominator"]) for row in result["hit_count_execution"]["distribution"]) == expected_distribution


def test_skill_link_precedes_loaded_dice_and_unknown_modifier_sources_fail_closed():
    state = _state(); pokemon = state["self_side"]["pokemon"][0]
    pokemon.update(current_ability="skill-link", known_item="loaded-dice")
    pokemon["known_item_provenance"]["status"] = "known"
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    resolved = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))
    assert resolved["status"] == "resolved"
    assert resolved["hit_count_execution"]["distribution"] == ({"hit_count": 5, "probability": {"numerator": 1, "denominator": 1}},)

    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state)); action = _action(d0)
    critical = freeze_runtime_d0_critical_hit_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"], move_metadata=action["move_metadata_authority"]["metadata"])
    critical["source_authority"]["attacker_item"] = {"status": "unknown"}
    incomplete = freeze_runtime_d0_variable_multi_hit_count_modifier_authority(strategy_d0=d0, runtime_snapshot=snapshot, attacker=d0["decision_owner"], target=d0["active_owners"]["opponent"], move_metadata=action["move_metadata_authority"]["metadata"], critical_hit_authority=critical)
    assert incomplete["status"] == "incomplete" and incomplete["reason"] == "variable_multi_hit_attacker_item_unknown"


def test_stale_or_conflicting_bindings_fail_closed_without_mutation():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state)); action = _action(d0)
    result = freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)
    assert result["attacker"]["pokemon_id"] == "attacker"
    state["self_side"]["pokemon"][0]["current_hp"] = 1
    assert freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), action=action)["status"] == "rejected"
    conflicting = deepcopy(action); conflicting["move_metadata_authority"]["metadata"]["move_id"] = "rock-blast"
    assert freeze_runtime_d0_variable_two_to_five_hit_count_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=conflicting)["status"] == "rejected"
