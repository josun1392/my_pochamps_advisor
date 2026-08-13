"""Bounded Ice Body recovery at the explicit first end-of-turn phase."""

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


def _known_snow_authority(manager, boundary, *, opponent_ability="pressure", weather="snow"):
    _apply(manager, _ability(boundary, "self", "pikachu", "ice-body"))
    _apply(manager, _ability(boundary, "opponent", "eevee", opponent_ability))
    _apply(manager, _weather(boundary, weather))


def _result(manager):
    return manager.read_state()["state"]["ice_body_end_of_turn_context"][-1]


def test_ice_body_recovers_authoritative_hp_clamps_and_snapshot_is_detached():
    manager, boundary = _manager(hp=95), _boundary()
    _known_snow_authority(manager, boundary)
    _apply(manager, _phase(boundary))
    state = manager.read_state()["state"]
    result = _result(manager)
    assert result["outcome"] == "recovered" and result["recovery"] == 6 and result["post_hp"] == 100
    frozen = build_runtime_advice_state_projection(state)["runtime_advice_state"]
    _apply(manager, _hp(boundary, 100, 90))
    assert frozen["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 100}


def test_ice_body_full_hp_and_exact_non_activation_cases_do_not_recover():
    full, boundary = _manager(hp=100), _boundary()
    _known_snow_authority(full, boundary)
    _apply(full, _phase(boundary))
    assert _result(full)["outcome"] == "already_full_hp" and _result(full)["recovery"] == 0

    rain, boundary = _manager(), _boundary()
    _known_snow_authority(rain, boundary, weather="rain")
    _apply(rain, _phase(boundary))
    assert rain.read_state()["state"].get("ice_body_end_of_turn_context", []) == []

    different_ability, boundary = _manager(), _boundary()
    _apply(different_ability, _ability(boundary, "self", "pikachu", "pressure"))
    _apply(different_ability, _ability(boundary, "opponent", "eevee", "pressure"))
    _apply(different_ability, _weather(boundary, "snow"))
    _apply(different_ability, _phase(boundary))
    assert different_ability.read_state()["state"].get("ice_body_end_of_turn_context", []) == []


def test_ice_body_weather_suppression_and_unknown_authority_remain_conservative():
    for suppressor, outcome in (("cloud-nine", "suppressed_by_weather_ability"), ("air-lock", "suppressed_by_weather_ability"), ("neutralizing-gas", "suppressed_by_neutralizing_gas")):
        manager, boundary = _manager(), _boundary()
        _known_snow_authority(manager, boundary, opponent_ability=suppressor)
        _apply(manager, _phase(boundary))
        assert _result(manager)["outcome"] == outcome and manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80

    weather_unknown, boundary = _manager(), _boundary()
    _apply(weather_unknown, _ability(boundary, "self", "pikachu", "ice-body"))
    _apply(weather_unknown, _phase(boundary))
    assert _result(weather_unknown)["reason"] == "current_weather_unknown"

    suppression_unknown, boundary = _manager(), _boundary()
    _apply(suppression_unknown, _ability(boundary, "self", "pikachu", "ice-body"))
    _apply(suppression_unknown, _weather(boundary, "snow"))
    _apply(suppression_unknown, _phase(boundary))
    assert _result(suppression_unknown)["reason"] == "current_ability_unknown"


def test_ice_body_faint_and_unordered_same_owner_residual_do_not_fabricate_recovery():
    fainted, boundary = _manager(hp=0, fainted=True), _boundary()
    _apply(fainted, _ability(boundary, "opponent", "eevee", "pressure"))
    _apply(fainted, _weather(boundary, "snow"))
    _apply(fainted, _phase(boundary))
    assert fainted.read_state()["state"].get("ice_body_end_of_turn_context", []) == []

    ordered, boundary = _manager(condition="poison"), _boundary()
    _known_snow_authority(ordered, boundary)
    _apply(ordered, _phase(boundary))
    result = _result(ordered)
    assert result["status"] == "incomplete" and result["reason"] == "same_owner_end_of_turn_order_unknown"
    assert ordered.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
