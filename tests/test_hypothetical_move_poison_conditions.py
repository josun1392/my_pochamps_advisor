from copy import deepcopy

from llm.advisor_hypothetical_condition_effects import apply_predicted_condition, project_move_poison_condition
from llm.advisor_hypothetical_direct_mechanics import evaluate_hypothetical_direct_mechanics
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _owner(side, pokemon):
    return {"session_id": "branch-session", "side": side, "slot_index": 0 if side == "self" else 1, "pokemon_id": pokemon}


def _state(*, target_types=("normal",), self_ability="blaze", target_ability="blaze", target_condition="none"):
    self_owner, target_owner = _owner("self", "salazzle"), _owner("opponent", "arcanine")
    condition = lambda side, value: {"side": side, "condition_type": value, "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}
    ability = lambda side, value: {"side": side, "ability": value, "status": "user_confirmed", "source": "user_confirmed_current_ability", "confidence": "known"}
    type_entry = lambda side, values: {"side": side, "state": "known", "types": list(values), "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current", "confidence": "known"}
    return {
        "schema_version": "deterministic-transition-preview-v1",
        "active": {"self": {**self_owner, "current_hp": 100, "max_hp": 100, "fainted": False}, "opponent": {**target_owner, "current_hp": 100, "max_hp": 100, "fainted": False}},
        "current_state": {"current_state_session_id": "branch-session", "condition_context": {"current_conditions": [condition("self", "none"), condition("opponent", target_condition)]}, "ability_context": {"current_abilities": [ability("self", self_ability), ability("opponent", target_ability)]}, "current_type_context": {"current_types": [type_entry("self", ("poison",)), type_entry("opponent", target_types)]}},
    }


def _action(*, ailment="poison", accuracy=None):
    return {"owner": _owner("self", "salazzle"), "move": {"move_id": "metadata-backed-status", "slot_index": 0, "priority": 0, "category": "status", "target": "selected-pokemon", "accuracy": accuracy, "effect_category": "ailment", "ailment": ailment}}


def _effect(state, action=None):
    return project_move_poison_condition(branch_state=state, action=action or _action(), expected_owner=_owner("self", "salazzle"), target_owner=_owner("opponent", "arcanine"))


def test_move_poison_applies_only_from_exact_metadata_and_no_accuracy_roll():
    state = _state(); before = deepcopy(state)
    effect = _effect(state)
    assert effect["status"] == "resolved" and effect["applicable"] is True and effect["ailment"] == "poison"
    assert _effect(state, _action(accuracy=100)) == {"status": "incomplete", "reason": "move_poison_success_uncertain"}
    assert _effect(state, _action(ailment="burn"))["status"] == "unsupported"
    apply_predicted_condition(state, effect, source_snapshot_fingerprint="source-fingerprint", branch_state_fingerprint=fingerprint_transition_preview_state(state))
    predicted = state["predicted_condition_context"]
    assert predicted["provenance"] == "turn_engine_predicted_move_poison" and predicted["condition_type"] == "poison"
    assert before["current_state"]["condition_context"] == state["current_state"]["condition_context"]
    assert "toxic" not in predicted and "residual" not in predicted and "counter" not in predicted


def test_poison_type_immunity_corrosion_and_immunity_are_exact_and_fail_closed():
    assert _effect(_state(target_types=("poison",)))["reason"] == "blocked_by_poison_type_immunity"
    assert _effect(_state(target_types=("steel",)))["reason"] == "blocked_by_poison_type_immunity"
    assert _effect(_state(target_types=("poison",), self_ability="corrosion"))["applicable"] is True
    blocked = _effect(_state(target_types=("steel",), self_ability="corrosion", target_ability="immunity"))
    assert blocked["reason"] == "blocked_by_immunity" and blocked["applicable"] is False
    unknown_attacker = _effect(_state(target_types=("poison",), self_ability="unknown"))
    assert unknown_attacker == {"status": "incomplete", "reason": "self.ability"}
    unknown_target = _effect(_state(target_ability="unknown"))
    assert unknown_target == {"status": "incomplete", "reason": "opponent.ability"}


def test_existing_condition_stale_owner_and_malformed_type_fail_closed():
    assert _effect(_state(target_condition="burn"))["reason"] == "target_existing_nonvolatile_condition"
    state = _state(); state["current_state"]["current_type_context"]["current_types"][1]["state"] = "unknown"
    assert _effect(state) == {"status": "incomplete", "reason": "opponent.current_type"}
    stale = _action(); stale["owner"]["pokemon_id"] = "replacement"
    assert _effect(_state(), stale)["status"] == "rejected"


def test_predicted_poison_is_consumed_only_by_private_hypothetical_calculator_view():
    state = _state()
    effect = _effect(state)
    # Applicability consumed exact ability authority already; this direct-Q12
    # fixture uses its independent known-absent ability context below.
    state["current_state"].pop("ability_context")
    absent = {"status": "known_absent"}
    state["current_state"]["direct_mechanics_context"] = {
        "generation": "gen9",
        "attacker": {"ability": absent, "item": absent, "boosts": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": 100, "max_hp": 100, "status": absent},
        "defender": {"ability": absent, "item": absent, "boosts": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0}, "current_hp": 100, "max_hp": 100, "status": absent},
        "field": {"weather": absent, "terrain": absent},
    }
    apply_predicted_condition(state, effect, source_snapshot_fingerprint="source", branch_state_fingerprint=fingerprint_transition_preview_state(state))
    action = {"owner": _owner("self", "salazzle"), "move": {"move_id": "venoshock", "slot_index": 1, "priority": 0, "category": "special"}}
    stats = {"hp": 100, "attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}
    result = evaluate_hypothetical_direct_mechanics(
        branch_state=state, source_snapshot_fingerprint="source", action=action, expected_owner=action["owner"],
        direct_evaluation_input={"source_snapshot_fingerprint": "source", "owner": action["owner"], "move_metadata": {**action["move"], "power": 65, "type": "poison"}, "stat_provenance": {"attacker": {"pokemon_identity": "salazzle", "types": {"available": True, "value": ["poison"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "arcanine", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50},
    )
    assert result["status"] == "known", result
    without_overlay = deepcopy(state); without_overlay.pop("predicted_condition_context")
    baseline = evaluate_hypothetical_direct_mechanics(
        branch_state=without_overlay, source_snapshot_fingerprint="source", action=action, expected_owner=action["owner"],
        direct_evaluation_input={"source_snapshot_fingerprint": "source", "owner": action["owner"], "move_metadata": {**action["move"], "power": 65, "type": "poison"}, "stat_provenance": {"attacker": {"pokemon_identity": "salazzle", "types": {"available": True, "value": ["poison"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "arcanine", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50},
    )
    assert baseline["status"] == "known" and result["mechanics_result"]["damage_range"]["minimum"] > baseline["mechanics_result"]["damage_range"]["minimum"]
    assert state["current_state"]["condition_context"]["current_conditions"][1]["condition_type"] == "none"
    stale = deepcopy(state); stale["predicted_condition_context"]["branch_state_fingerprint"] = "stale"
    assert evaluate_hypothetical_direct_mechanics(branch_state=stale, source_snapshot_fingerprint="source", action=action, expected_owner=action["owner"], direct_evaluation_input={"source_snapshot_fingerprint": "source", "owner": action["owner"], "move_metadata": {**action["move"], "power": 65, "type": "poison"}, "stat_provenance": {"attacker": {"pokemon_identity": "salazzle", "types": {"available": True, "value": ["poison"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}, "defender": {"pokemon_identity": "arcanine", "types": {"available": True, "value": ["normal"]}, "final_stats": {"available": True, "value": stats}, "known_item": {"status": "known_absent"}}}, "trusted_level": 50})["reason"] == "predicted_condition_branch_mismatch"
