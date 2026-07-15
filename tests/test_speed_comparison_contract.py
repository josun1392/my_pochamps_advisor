from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_effective_stat_inputs


def _final(side: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": "speed", "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _stage(side: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": "speed", "stage": value, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"}


@pytest.mark.parametrize(("self_speed", "opponent_speed", "stages", "result"), [
    (167, 201, [], "opponent_faster"), (167, 201, [_stage("self", 2)], "self_faster"),
    (201, 201, [], "tie"), (167, 201, [_stage("opponent", -1)], "self_faster"),
])
def test_speed_comparison_is_stage_only(self_speed: int, opponent_speed: int, stages: list[dict[str, object]], result: str) -> None:
    context = build_effective_stat_inputs({"current_final_stats": [_final("self", self_speed), _final("opponent", opponent_speed)]}, {"current_stages": stages})
    assert context is not None
    assert context["speed_comparison"]["result"] == result
    assert context["speed_comparison"]["calculation_scope"] == "stage_only"


@pytest.mark.parametrize("entries", [[_final("self", 167)], [_final("opponent", 201)]])
def test_speed_comparison_is_unavailable_without_both_final_speeds(entries: list[dict[str, object]]) -> None:
    context = build_effective_stat_inputs({"current_final_stats": entries})
    assert context is not None
    assert context["speed_comparison"] == {"calculation_scope": "stage_only", "calculation_status": "unavailable", "result": "unavailable", **({"self_effective_speed": 167} if entries[0]["side"] == "self" else {"opponent_effective_speed": 201})}
