from llm.advisor_battle_state_context import build_deterministic_hit_chance_assessment


def test_accuracy_uses_only_metadata_and_missing_is_unavailable() -> None:
    assert build_deterministic_hit_chance_assessment({"move_id": "stone-edge", "accuracy": None}, None)["reason"] == "missing_move_accuracy"
    assert build_deterministic_hit_chance_assessment({"move_id": "aerial-ace", "always_hit": True}, None)["reason"] == "move_always_hits"
