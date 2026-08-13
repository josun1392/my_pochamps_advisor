"""Bounded Solar Power damage at the explicit first end-of-turn phase."""

from advisor.damage.ability_modifiers import get_spa_ability_modifier
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE,
    CURRENT_WEATHER_SOURCE,
    FIRST_END_OF_TURN_SOURCE,
    HP_TRANSITION_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection


def _manager(*, hp=80, fainted=False, condition=None):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=100, fainted=fainted)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    if condition is not None:
        state["self_side"]["pokemon"][0]["condition"] = condition
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _ability(boundary, side, pokemon_id, ability, turn=4):
    return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pokemon_id, turn_number=turn)


def _weather(boundary, weather, turn=4):
    return boundary.confirm(event_kind="current_weather_observed", payload={"weather": weather}, session_id="s", source=CURRENT_WEATHER_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _phase(boundary, turn=4):
    return boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _hp(boundary, before, after, turn=5):
    return boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": before, "hp_after": after}, session_id="s", source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=turn)


def _known_sun_authority(manager, boundary, *, opponent_ability="pressure", weather="sun"):
    _apply(manager, _ability(boundary, "self", "pikachu", "solar-power"))
    _apply(manager, _ability(boundary, "opponent", "eevee", opponent_ability))
    _apply(manager, _weather(boundary, weather))


def _result(manager):
    return manager.read_state()["state"]["solar_power_end_of_turn_context"][-1]


def test_solar_power_damages_authoritative_hp_and_preserves_direct_sun_modifier():
    manager, boundary = _manager(), _boundary()
    _known_sun_authority(manager, boundary)
    _apply(manager, _phase(boundary))
    state = manager.read_state()["state"]
    result = _result(manager)
    assert result["outcome"] == "damaged" and result["damage"] == 12 and result["post_hp"] == 68 and result["guaranteed_ko"] is False
    frozen = build_runtime_advice_state_projection(state)["runtime_advice_state"]
    _apply(manager, _hp(boundary, 68, 60))
    assert frozen["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 68}
    assert get_spa_ability_modifier("solar-power", weather="sun") == 6144


def test_solar_power_lethal_damage_non_sun_and_non_solar_power_cases():
    lethal, boundary = _manager(hp=10), _boundary()
    _known_sun_authority(lethal, boundary)
    _apply(lethal, _phase(boundary))
    assert _result(lethal)["post_hp"] == 0 and _result(lethal)["guaranteed_ko"] is True
    assert lethal.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 0

    rain, boundary = _manager(), _boundary()
    _known_sun_authority(rain, boundary, weather="rain")
    _apply(rain, _phase(boundary))
    assert rain.read_state()["state"].get("solar_power_end_of_turn_context", []) == []

    different_ability, boundary = _manager(), _boundary()
    _apply(different_ability, _ability(boundary, "self", "pikachu", "pressure"))
    _apply(different_ability, _ability(boundary, "opponent", "eevee", "pressure"))
    _apply(different_ability, _weather(boundary, "sun"))
    _apply(different_ability, _phase(boundary))
    assert different_ability.read_state()["state"].get("solar_power_end_of_turn_context", []) == []


def test_solar_power_suppression_and_unknown_authority_remain_conservative():
    for suppressor, outcome in (("cloud-nine", "suppressed_by_weather_ability"), ("air-lock", "suppressed_by_weather_ability"), ("neutralizing-gas", "suppressed_by_neutralizing_gas")):
        manager, boundary = _manager(), _boundary()
        _known_sun_authority(manager, boundary, opponent_ability=suppressor)
        _apply(manager, _phase(boundary))
        assert _result(manager)["outcome"] == outcome and manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80

    weather_unknown, boundary = _manager(), _boundary()
    _apply(weather_unknown, _ability(boundary, "self", "pikachu", "solar-power"))
    _apply(weather_unknown, _phase(boundary))
    assert _result(weather_unknown)["reason"] == "current_weather_unknown"

    suppression_unknown, boundary = _manager(), _boundary()
    _apply(suppression_unknown, _ability(boundary, "self", "pikachu", "solar-power"))
    _apply(suppression_unknown, _weather(boundary, "sun"))
    _apply(suppression_unknown, _phase(boundary))
    assert _result(suppression_unknown)["reason"] == "current_ability_unknown"


def test_solar_power_faint_and_unordered_same_owner_residual_do_not_fabricate_damage():
    fainted, boundary = _manager(hp=0, fainted=True), _boundary()
    _apply(fainted, _ability(boundary, "opponent", "eevee", "pressure"))
    _apply(fainted, _weather(boundary, "sun"))
    _apply(fainted, _phase(boundary))
    assert fainted.read_state()["state"].get("solar_power_end_of_turn_context", []) == []

    ordered, boundary = _manager(condition="poison"), _boundary()
    _known_sun_authority(ordered, boundary)
    _apply(ordered, _phase(boundary))
    result = _result(ordered)
    assert result["status"] == "incomplete" and result["reason"] == "same_owner_end_of_turn_order_unknown"
    assert ordered.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
