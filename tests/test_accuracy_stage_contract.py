from llm.advisor_battle_state_context import build_deterministic_hit_chance_assessment


def _stages(accuracy, evasion):
    return {"current_stages": [{"side": "self", "stat": "accuracy", "stage": accuracy, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}, {"side": "opponent", "stat": "evasion", "stage": evasion, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"}]}


def test_accuracy_and_evasion_stages_use_existing_neutral_default_and_clamp() -> None:
    assessment = build_deterministic_hit_chance_assessment({"move_id": "stone-edge", "accuracy": 80}, _stages(6, -6))
    assert assessment["net_stage"] == 6 and assessment["hit_chance_percent"] == 100
    assert build_deterministic_hit_chance_assessment({"move_id": "x", "accuracy": 80}, _stages(-6, 6))["net_stage"] == -6
