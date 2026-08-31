from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_escalating_three_hit_execution_authority import (
    SCHEMA_VERSION,
    freeze_runtime_d0_escalating_three_hit_execution_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def _state():
    state = create_unknown_bootstrap_battle_state("escalating-three-hit", "attacker", "target")["state"]
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


def _action(d0, move_id="triple-axel", **overrides):
    powers = {"triple-axel": (20, "ice"), "triple-kick": (10, "fighting")}
    power, move_type = powers.get(move_id, (20, "normal"))
    move = {"move_id": move_id, "category": "physical", "power": power, "type": move_type, "accuracy": 90, "priority": 0, "min_hits": 3, "max_hits": 3, "bp_escalation": True, "multiaccuracy": True}
    move.update(overrides)
    authority = {"status": "resolved", "schema_version": "runtime-d0-selectable-move-metadata-authority-v1", "candidate_id": f"attack:{move_id}", "move_id": move_id, "metadata": move, "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(d0["decision_owner"]), "active_attacker": deepcopy(d0["decision_owner"])}
    return {"action_id": f"attack:{move_id}", "action_type": "attack", "identity": move_id, "move_metadata_authority": authority}


@pytest.mark.parametrize(("move_id", "powers"), [("triple-axel", [20, 40, 60]), ("triple-kick", [10, 20, 30])])
def test_canonical_escalating_moves_freeze_ordered_power_accuracy_and_critical_authority(move_id, powers):
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    result = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, move_id))
    assert result["status"] == "resolved" and result["schema_version"] == SCHEMA_VERSION
    assert result["hit_count_execution"]["maximum_hits"] == 3
    assert [row["base_power"] for row in result["per_hit_power_execution"]["hits"]] == powers
    accuracy = result["per_attempt_accuracy_execution"]
    assert accuracy["semantics"] == "independent_accuracy_check_per_hit_stop_on_first_miss"
    assert accuracy["hit_probability"] == {"numerator": 9, "denominator": 10}
    assert accuracy["miss_probability"] == {"numerator": 1, "denominator": 10}
    assert accuracy["root_mass"] == {"numerator": 1, "denominator": 1}
    assert result["per_hit_critical_execution"]["semantics"] == "independent_canonical_critical_roll_per_landed_hit"


def test_missing_or_noncanonical_metadata_remains_fail_closed():
    state = _state(); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, min_hits=None))["reason"] == "escalating_three_hit_count_metadata_missing"
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, bp_escalation=False))["reason"] == "escalating_three_hit_noncanonical_timing_metadata"
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0, "double-hit", min_hits=2, max_hits=2))["reason"] == "escalating_three_hit_move_not_in_supported_execution_catalog"


def test_skill_link_and_loaded_dice_select_one_initial_accuracy_plan():
    for ability, item in (("skill-link", None), ("pressure", "loaded-dice"), ("skill-link", "loaded-dice")):
        state = _state(); pokemon = state["self_side"]["pokemon"][0]; pokemon["current_ability"] = ability; pokemon["known_item"] = item
        if item: pokemon["known_item_provenance"]["status"] = "known"
        snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
        plan = freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=_action(d0))["modifier_authority"]
        assert plan["execution_plan"] == "single_initial_accuracy_then_guaranteed_remaining_hits"


def test_stale_and_conflicting_bindings_reject_without_mutation():
    state = _state(); original = deepcopy(state); snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state)); action = _action(d0)
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=action)["status"] == "resolved"
    assert state == original
    state["self_side"]["pokemon"][0]["current_hp"] = 1
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=_snapshot(state), action=action)["status"] == "rejected"
    conflicting = deepcopy(action); conflicting["move_metadata_authority"]["metadata"]["move_id"] = "triple-kick"
    assert freeze_runtime_d0_escalating_three_hit_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=conflicting)["status"] == "rejected"
