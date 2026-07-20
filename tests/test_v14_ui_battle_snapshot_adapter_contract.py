from copy import deepcopy

import pytest

from llm.advisor_candidate_contract import adapt_ui_battle_snapshot, build_ui_recommendation_snapshot_summary


def _input():
    return {"scenario": {"mode": "advisor", "format_note": "trusted", "known_limitations": ["known"]}, "pokemon": {"my_active": {"name_en": "a"}, "opponent_active": {"name_en": "b"}}, "final_stat_context": {"current_final_stats": []}, "condition_context": {"current_conditions": []}, "moves": {"opponent_selected_move": {"move_id": "tackle"}}, "model": "forbidden", "raw_response": "forbidden", "worker": object()}


def test_snapshot_copies_only_trusted_deterministic_fields_without_mutation():
    battle_input = _input(); before = deepcopy({key: value for key, value in battle_input.items() if key != "worker"})
    snapshot = adapt_ui_battle_snapshot(battle_input=battle_input)
    summary = build_ui_recommendation_snapshot_summary(battle_input=battle_input)
    battle_input["pokemon"]["my_active"]["name_en"] = "mutated"
    assert snapshot["pokemon"]["my_active"]["name_en"] == "a" and snapshot["opponent_selected_move"] == {"move_id": "tackle"}
    assert "model" not in snapshot and "raw_response" not in snapshot and "worker" not in snapshot
    assert summary == {"scenario": {"mode": "advisor", "format_note": "trusted"}, "pokemon": before["pokemon"]}


def test_missing_selected_pokemon_and_non_mapping_input_are_sanitized():
    with pytest.raises(ValueError): adapt_ui_battle_snapshot(battle_input={})
    with pytest.raises(ValueError): adapt_ui_battle_snapshot(battle_input=None)
