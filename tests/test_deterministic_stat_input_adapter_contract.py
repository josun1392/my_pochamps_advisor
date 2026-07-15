from __future__ import annotations

from llm.advisor_battle_state_context import build_deterministic_stat_inputs, build_final_stat_context_from_confirmations


def test_adapter_exposes_final_stats_and_stages_without_applying_any_multiplier() -> None:
    final_context = build_final_stat_context_from_confirmations([{"side": "self", "stat": "attack", "value": 205, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}])
    stage_context = {"current_stages": [{"side": "self", "stat": "attack", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}]}
    assert build_deterministic_stat_inputs(final_context, stage_context) == {"base_final_stats": {"self": {"attack": 205}}, "current_stat_stages": {"self": {"attack": -1}}}
