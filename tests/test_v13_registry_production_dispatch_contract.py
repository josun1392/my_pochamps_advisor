from __future__ import annotations

import pytest

import llm.advisor_battle_state_context as battle_context


def _stat(side: str, stat: str, value: int) -> dict[str, object]:
    return {"side": side, "stat": stat, "value": value, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "confidence": "known"}


def _final_stats() -> dict[str, object]:
    return {"current_final_stats": [
        _stat("self", "attack", 200), _stat("self", "special-attack", 200), _stat("self", "speed", 200),
        _stat("opponent", "defense", 150), _stat("opponent", "special-defense", 150), _stat("opponent", "speed", 100),
    ]}


@pytest.mark.parametrize(("move_id", "family", "assessment_key", "expected_power", "kwargs"), [
    ("eruption", "current_hp_based_power", "current_hp_based_power_assessment", 150, {"current_hp_context": {"current_hp": [{"side": "self", "current_hp": 100, "maximum_hp": 100}]}}),
    ("electro-ball", "speed_based_power", "speed_based_power_assessment", 80, {}),
    ("heavy-slam", "weight_based_power", "weight_based_power_assessment", 120, {"weight_context": {"self_weight": 1000, "opponent_weight": 100}}),
    ("low-kick", "target_weight_power", "target_weight_power_assessment", 120, {"weight_context": {"opponent_weight": 2000}}),
    ("stored-power", "positive_stage_sum_power", "positive_stage_sum_power_assessment", 60, {"stat_stage_context": {"current_stages": [{"side":"self","stat":stat,"stage":2 if stat=="attack" else 0,"status":"user_confirmed","source":"user_confirmed_current_stat_stage","confidence":"known"} for stat in ("attack","defense","special-attack","special-defense","speed","accuracy","evasion")]}}),
    ("crush-grip", "target_hp_based_power", "target_hp_based_power_assessment", 121, {"current_hp_context": {"current_hp": [{"side": "opponent", "current_hp": 100, "maximum_hp": 100}]}}),
    ("weather-ball", "environment_based_move", "environment_based_move_assessment", 100, {"field_state_context": {"current_field": {"weather": "rain"}}}),
    ("facade", "binary_condition_power", "binary_condition_power_assessment", 140, {"condition_context": {"current_conditions": [{"side": "self", "condition_type": "burn"}]}}),
    ("avalanche", "turn_event_power", "turn_event_power_assessment", 120, {"turn_event_context": {"received_target_direct_damage": True}}),
    ("rage-fist", "battle_counter_power", "battle_counter_power_assessment", 100, {"battle_counter_context": {"rage_fist_hits_received": 1}}),
    ("fury-cutter", "consecutive_use_power", "consecutive_use_power_assessment", 80, {"consecutive_use_context": {"fury_cutter_consecutive_uses": 2}}),
])
def test_each_family_uses_one_registry_selected_resolver_and_propagates_power(
    monkeypatch: pytest.MonkeyPatch, move_id: str, family: str, assessment_key: str, expected_power: int, kwargs: dict[str, object],
) -> None:
    helper_names = {
        "current_hp_based_power": "build_current_hp_based_power_assessment", "speed_based_power": "build_speed_based_power_assessment",
        "weight_based_power": "build_weight_based_power_assessment", "stat_stage_based_power": "build_stat_stage_based_power_assessment",
        "target_weight_power": "build_target_weight_power_assessment",
        "positive_stage_sum_power": "build_positive_stage_sum_power_assessment",
        "target_hp_based_power": "build_target_hp_based_power_assessment", "environment_based_move": "build_environment_based_move_assessment",
        "binary_condition_power": "build_binary_condition_power_assessment", "turn_event_power": "build_turn_event_power_assessment",
        "battle_counter_power": "build_battle_counter_power_assessment", "consecutive_use_power": "build_consecutive_use_power_assessment",
    }
    calls = {name: 0 for name in helper_names}
    for candidate_family, helper_name in helper_names.items():
        original = getattr(battle_context, helper_name)

        def wrapped(*args: object, _original: object = original, _family: str = candidate_family, **inner_kwargs: object) -> object:
            calls[_family] += 1
            return _original(*args, **inner_kwargs)

        monkeypatch.setattr(battle_context, helper_name, wrapped)

    resolver_calls = 0
    original_resolver = battle_context.resolve_registered_dynamic_move

    def resolve_once(*args: object, **inner_kwargs: object) -> object:
        nonlocal resolver_calls
        resolver_calls += 1
        return original_resolver(*args, **inner_kwargs)

    captured_moves: list[dict[str, object]] = []

    def capture_effective_move(_stats: object, selected_move: dict[str, object] | None) -> None:
        captured_moves.append(dict(selected_move) if selected_move is not None else {})
        return None

    monkeypatch.setattr(battle_context, "resolve_registered_dynamic_move", resolve_once)
    monkeypatch.setattr(battle_context, "build_limited_damage_estimate", capture_effective_move)
    result = battle_context.build_deterministic_calculation_context(
        _final_stats(), selected_move={"move_id": move_id, "category": "physical", "power": 1, "type": "normal"}, **kwargs,
    )

    assert result is not None
    assert resolver_calls == 1
    assert calls[family] == 1
    assert sum(calls.values()) == 1
    assert result[assessment_key]["status"] == "resolved"
    assert captured_moves == [{"move_id": move_id, "category": "physical", "power": expected_power, "type": "water" if move_id == "weather-ball" else "normal"}]
