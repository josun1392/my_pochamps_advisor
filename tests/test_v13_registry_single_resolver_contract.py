from __future__ import annotations

import pytest

import llm.advisor_battle_state_context as battle_context


def _stat(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def test_ordinary_move_bypasses_registry_and_keeps_metadata_power_and_type(monkeypatch) -> None:
    final = {"current_final_stats": [_stat("self", "attack", 200), _stat("opponent", "defense", 150)]}
    captured: list[dict[str, object]] = []
    registry_lookups = 0

    original_resolver = battle_context.resolve_registered_dynamic_move

    def registry_lookup(*args: object, **kwargs: object) -> object:
        nonlocal registry_lookups
        registry_lookups += 1
        assert args[0]["move_id"] == "tackle"
        return original_resolver(*args, **kwargs)

    def capture(_stats: object, move: dict[str, object] | None) -> None:
        captured.append(dict(move) if move else {})
        return None

    monkeypatch.setattr(battle_context, "resolve_registered_dynamic_move", registry_lookup)
    for helper_name in (
        "build_current_hp_based_power_assessment", "build_speed_based_power_assessment", "build_weight_based_power_assessment", "build_target_weight_power_assessment",
        "build_stat_stage_based_power_assessment", "build_target_hp_based_power_assessment", "build_environment_based_move_assessment",
        "build_binary_condition_power_assessment", "build_turn_event_power_assessment", "build_battle_counter_power_assessment",
        "build_consecutive_use_power_assessment",
    ):
        monkeypatch.setattr(battle_context, helper_name, lambda *args, **kwargs: pytest.fail("ordinary move selected a dynamic family resolver"))
    monkeypatch.setattr(battle_context, "build_limited_damage_estimate", capture)
    result = battle_context.build_deterministic_calculation_context(final, selected_move={"move_id": "tackle", "category": "physical", "power": 40, "type": "normal"})

    assert result is not None
    assert registry_lookups == 1
    assert captured == [{"move_id": "tackle", "category": "physical", "power": 40, "type": "normal"}]
    assert not any(key.endswith("_power_assessment") or key == "environment_based_move_assessment" for key in result)
