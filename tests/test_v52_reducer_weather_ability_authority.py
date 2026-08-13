"""Explicit weather and active-ability authority remains lifecycle-owned and frozen."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE,
    CURRENT_WEATHER_SOURCE,
    SWITCH_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_roster_mechanics import build_self_roster_mechanics_context_projection
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
    state["self_side"]["pokemon"][1]["pokemon_id"] = "raichu"
    state["self_side"]["pokemon"][0]["known_item"] = "leftovers"
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary(pokemon_id="pikachu", slot=0):
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": slot, "pokemon_id": pokemon_id}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    return manager.apply("s", manager.read_collection_snapshot())


def _weather(boundary, weather, *, turn=1, session="s"):
    return boundary.confirm(event_kind="current_weather_observed", payload={"weather": weather}, session_id=session, source=CURRENT_WEATHER_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _ability(boundary, ability, *, turn=1, pokemon_id="pikachu", slot=0, session="s"):
    return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id=session, source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=slot, pokemon_id=pokemon_id, turn_number=turn)


def _frozen(manager, *, active="pikachu", slot=0):
    runtime = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    return build_turn_snapshot_from_battle_input({
        "pokemon": {"my_active": {"slot_index": slot, "name_en": active}, "opponent_active": {"slot_index": 0, "name_en": "eevee"}},
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": runtime,
    }).to_dict()["current_state"]


def test_current_weather_and_ability_start_unknown_then_trusted_observations_replace_them():
    manager, boundary = _manager(), _boundary()
    initial = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert initial["field"]["weather"] == {"status": "unknown"}
    assert initial["self"]["active_pokemon"]["current_ability"] == {"status": "unknown"}
    assert initial["self"]["active_pokemon"]["item"] == {"status": "known", "value": "leftovers"}

    assert _apply(manager, _weather(boundary, "sandstorm", turn=3))["status"] == "applied"
    assert _apply(manager, _ability(boundary, "magic-guard", turn=3))["status"] == "applied"
    assert _apply(manager, _weather(boundary, "none", turn=4))["status"] == "applied"
    assert _apply(manager, _ability(boundary, "overcoat", turn=4))["status"] == "applied"

    runtime = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert runtime["field"]["weather"] == {"status": "known", "value": "none"}
    assert runtime["self"]["active_pokemon"]["current_ability"] == {"status": "known", "value": "overcoat"}
    roster = build_self_roster_mechanics_context_projection(manager.read_state()["state"])
    assert roster["entries"][0]["ability_authority"] == {"status": "known", "value": "overcoat"}


def test_weather_and_ability_reject_stale_or_mismatched_observations():
    manager, boundary = _manager(), _boundary()
    assert _weather(boundary, "sandstorm", session="stale")["status"] == "stale_session"
    assert _ability(boundary, "magic-guard", pokemon_id="raichu")["status"] == "invalid_provenance"
    assert _apply(manager, _weather(boundary, "sandstorm", turn=4))["status"] == "applied"
    stale = _apply(manager, _weather(boundary, "rain", turn=3))
    assert stale["status"] == "transition_invalid"
    assert manager.read_state()["state"]["field"]["weather"] == "sandstorm"


def test_switch_does_not_inherit_ability_and_frozen_weather_ability_are_detached():
    manager, boundary = _manager(), _boundary()
    assert _apply(manager, _weather(boundary, "sandstorm", turn=2))["status"] == "applied"
    assert _apply(manager, _ability(boundary, "magic-guard", turn=2))["status"] == "applied"
    before = _frozen(manager)
    assert before["runtime_advice_state"]["field"]["weather"] == {"status": "known", "value": "sandstorm"}
    assert before["runtime_advice_state"]["self"]["active_pokemon"]["current_ability"] == {"status": "known", "value": "magic-guard"}

    switch = boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu")
    assert _apply(manager, switch)["status"] == "applied"
    replacement = _frozen(manager, active="raichu", slot=1)
    assert replacement["runtime_advice_state"]["self"]["active_pokemon"]["current_ability"] == {"status": "unknown"}
    assert _apply(manager, _weather(boundary, "rain", turn=3))["status"] == "applied"
    assert before["runtime_advice_state"]["field"]["weather"] == {"status": "known", "value": "sandstorm"}
    assert before["runtime_advice_state"]["self"]["active_pokemon"]["current_ability"] == {"status": "known", "value": "magic-guard"}
