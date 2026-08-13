"""Bounded Dry Skin Rain/Sun effects at the explicit first end-of-turn phase."""

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CURRENT_ABILITY_SOURCE, CURRENT_WEATHER_SOURCE, FIRST_END_OF_TURN_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection


def _manager(*, hp=80, fainted=False, condition=None):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=100, fainted=fainted)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, fainted=False)
    if condition is not None: state["self_side"]["pokemon"][0]["condition"] = condition
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary(): return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
def _apply(manager, value): assert manager.admit_confirmation("s", value)["status"] == "added"; assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"
def _ability(boundary, side, pid, ability): return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pid, turn_number=4)
def _weather(boundary, weather): return boundary.confirm(event_kind="current_weather_observed", payload={"weather": weather}, session_id="s", source=CURRENT_WEATHER_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4)
def _phase(boundary): return boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4)
def _known(manager, boundary, weather, opponent="pressure"):
    _apply(manager, _ability(boundary, "self", "pikachu", "dry-skin")); _apply(manager, _ability(boundary, "opponent", "eevee", opponent)); _apply(manager, _weather(boundary, weather))
def _result(manager): return manager.read_state()["state"]["dry_skin_end_of_turn_context"][-1]


def test_dry_skin_rain_heals_clamps_and_projects_authoritative_hp():
    manager, boundary = _manager(hp=95), _boundary(); _known(manager, boundary, "rain"); _apply(manager, _phase(boundary))
    result = _result(manager); state = manager.read_state()["state"]
    assert result["weather"] == "rain" and result["recovery"] == 12 and result["post_hp"] == 100 and result["guaranteed_ko"] is False
    assert build_runtime_advice_state_projection(state)["runtime_advice_state"]["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 100}


def test_dry_skin_rain_at_full_hp_resolves_without_change():
    manager, boundary = _manager(hp=100), _boundary(); _known(manager, boundary, "rain"); _apply(manager, _phase(boundary))
    result = _result(manager)
    assert result["outcome"] == "already_full_hp" and result["recovery"] == 0 and result["post_hp"] == 100


def test_dry_skin_sun_damages_and_can_prove_lethal_ko():
    manager, boundary = _manager(hp=10), _boundary(); _known(manager, boundary, "sun"); _apply(manager, _phase(boundary))
    result = _result(manager)
    assert result["weather"] == "sun" and result["damage"] == 12 and result["post_hp"] == 0 and result["guaranteed_ko"] is True
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 0


@pytest.mark.parametrize("weather", ["none", "snow", "sandstorm"])
def test_dry_skin_other_exact_weather_and_exact_different_ability_do_not_activate(weather):
    manager, boundary = _manager(), _boundary(); _known(manager, boundary, weather); _apply(manager, _phase(boundary))
    assert manager.read_state()["state"].get("dry_skin_end_of_turn_context", []) == []
    other, boundary = _manager(), _boundary(); _apply(other, _ability(boundary, "self", "pikachu", "pressure")); _apply(other, _ability(boundary, "opponent", "eevee", "pressure")); _apply(other, _weather(boundary, "rain")); _apply(other, _phase(boundary))
    assert other.read_state()["state"].get("dry_skin_end_of_turn_context", []) == []


@pytest.mark.parametrize("weather", ["rain", "sun"])
@pytest.mark.parametrize("suppressor", ["cloud-nine", "air-lock", "neutralizing-gas"])
def test_dry_skin_suppression_and_unknown_authority_are_conservative(weather, suppressor):
    manager, boundary = _manager(), _boundary(); _known(manager, boundary, weather, suppressor); _apply(manager, _phase(boundary))
    assert _result(manager)["outcome"].startswith("suppressed") and manager.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
    unknown_weather, boundary = _manager(), _boundary(); _apply(unknown_weather, _ability(boundary, "self", "pikachu", "dry-skin")); _apply(unknown_weather, _phase(boundary))
    assert _result(unknown_weather)["reason"] == "current_weather_unknown"
    unknown_suppression, boundary = _manager(), _boundary(); _apply(unknown_suppression, _ability(boundary, "self", "pikachu", "dry-skin")); _apply(unknown_suppression, _weather(boundary, weather)); _apply(unknown_suppression, _phase(boundary))
    assert _result(unknown_suppression)["reason"] == "current_ability_unknown"


def test_dry_skin_faint_and_unordered_same_owner_residual_do_not_apply():
    fainted, boundary = _manager(hp=0, fainted=True), _boundary(); _apply(fainted, _ability(boundary, "opponent", "eevee", "pressure")); _apply(fainted, _weather(boundary, "rain")); _apply(fainted, _phase(boundary))
    assert fainted.read_state()["state"].get("dry_skin_end_of_turn_context", []) == []
    ordered, boundary = _manager(condition="poison"), _boundary(); _known(ordered, boundary, "sun"); _apply(ordered, _phase(boundary))
    assert _result(ordered)["status"] == "incomplete" and ordered.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
